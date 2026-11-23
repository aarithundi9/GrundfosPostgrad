"""DONE (data loading is now central). Load NREL ComStock + ResStock 15-min profiles -> ``hourly_profiles`` table.

Run: ``python scripts/download_nrel.py`` first (files land in data/raw/nrel/).

Column names below were checked against the actual files on OEDI (Nov 2026).
Gotchas found while checking:
  * ComStock 2025 R3 columns end in ``.kwh``; ResStock 2021 R1 columns have no suffix
    but are also kWh (data_dictionary.tsv).
  * ResStock 2021 by-PUMA aggregates are AVERAGE PER DWELLING UNIT, not stock totals
    (multifamily 5+ in PUMA 3807 sums to ~12.8 MWh site energy per year: per-unit scale).
    Multiply by ``units_represented`` to get the stock total. ComStock values are stock
    totals (divide by ``floor_area_represented`` for kWh/sqft).
  * Both datasets: 35,040 rows, period-ending EST, 2018-01-01 00:15 ... 2019-01-01 00:00.
  * The ResStock 2025 release has NO by-PUMA files, so 2021 R1 is the only PUMA-level
    residential option. Its README marks it superseded; note this in the limitations.

Steps (from the Week 2 plan, updated with decisions D1-D3):
  1. For each PUMA in settings.nrel (primary first) and each profile type, read the CSV.
  2. Sum fuel columns to SPACE_HEATING_FUEL and DHW_FUEL (fuel consumed, kWh).
     Fans and pumps are NOT heat (exclude); hot tub excluded.
  3. Convert fuel -> delivered heat per fuel with settings.heat.efficiency (D2):
     space_heating_kwh = sum_f(fuel_f * eff_f); same for dhw_kwh.
     heat_total_kwh = space_heating_kwh + dhw_kwh (D1).
  4. ResStock: multiply by units_represented. Set scale_basis/scale_value:
     ComStock -> ("floor_area_sqft", floor_area_represented);
     ResStock -> ("dwelling_units", units_represented).
  5. 15-min -> hourly with heatreuse.timeutils.to_hourly (hour-ending, NOT resample left).
  6. Flag low_model_count = models_used < settings.nrel.min_models_used.
  7. heatreuse.timeutils.check_hourly(df, by=["puma", "profile_type"]) then
     heatreuse.io.write_table(df, "hourly_profiles").
  8. Also write ``fuel_heat_fractions`` (annual heating+DHW share of each fuel's total):
     Rafa uses it instead of the national EIA 68-69% gas-for-heating figure.
"""

from __future__ import annotations

import pandas as pd

from heatreuse import config, timeutils

FUELS = ["natural_gas", "fuel_oil", "propane", "district_heating", "electricity", "wood"]

# ComStock 2025 release 3 (stock totals, kWh)
COMSTOCK_SPACE_HEATING = {
    "natural_gas": ["out.natural_gas.heating.energy_consumption.kwh"],
    "fuel_oil": ["out.fuel_oil.heating.energy_consumption.kwh"],
    "propane": ["out.propane.heating.energy_consumption.kwh"],
    "district_heating": ["out.district_heating.heating.energy_consumption.kwh"],
    "electricity": ["out.electricity.heating.energy_consumption.kwh"],
}
COMSTOCK_DHW = {
    "natural_gas": ["out.natural_gas.water_systems.energy_consumption.kwh"],
    "fuel_oil": ["out.fuel_oil.water_systems.energy_consumption.kwh"],
    "propane": ["out.propane.water_systems.energy_consumption.kwh"],
    "district_heating": ["out.district_heating.water_systems.energy_consumption.kwh"],
    "electricity": ["out.electricity.water_systems.energy_consumption.kwh"],
}
COMSTOCK_FUEL_TOTAL = {f: [f"out.{f}.total.energy_consumption.kwh"] for f in FUELS[:5]}

# ResStock 2021 release 1 (PER DWELLING UNIT, kWh, no unit suffix)
RESSTOCK_SPACE_HEATING = {
    "natural_gas": ["out.natural_gas.heating.energy_consumption"],
    "fuel_oil": ["out.fuel_oil.heating.energy_consumption"],
    "propane": ["out.propane.heating.energy_consumption"],
    "electricity": ["out.electricity.heating.energy_consumption",
                    "out.electricity.heating_supplement.energy_consumption"],
    "wood": ["out.wood.heating.energy_consumption"],
}
RESSTOCK_DHW = {
    "natural_gas": ["out.natural_gas.water_systems.energy_consumption"],
    "fuel_oil": ["out.fuel_oil.water_systems.energy_consumption"],
    "propane": ["out.propane.water_systems.energy_consumption"],
    "electricity": ["out.electricity.water_systems.energy_consumption"],
}
RESSTOCK_FUEL_TOTAL = {f: [f"out.{f}.total.energy_consumption"] for f in
                       ["natural_gas", "fuel_oil", "propane", "electricity", "wood"]}
# Excluded on purpose (not delivered heat): fans_heating, pumps_heating, hot_tub_*, pool_*.

PROFILE_TYPE_FROM_FILE = {
    # ResStock file stem -> profile_type (ComStock stems are already the profile_type)
    "multi-family_with_5plus_units": "multi-family_with_5plus_units",
    "multi-family_with_2_-_4_units": "multi-family_with_2_-_4_units",
    "single-family_attached": "single-family_attached",
    "single-family_detached": "single-family_detached",
    "mobile_home": "mobile_home",
}


def _heat_columns(df: pd.DataFrame, space: dict, dhw: dict, scale: float) -> pd.DataFrame:
    """Fuel and delivered-heat columns (kWh) from raw NREL columns."""
    eff = config.load_settings()["heat"]["efficiency"]
    out = pd.DataFrame({"timestamp": df["timestamp"]})
    space_fuel = space_heat = dhw_fuel = dhw_heat = 0.0
    for fuel, cols in space.items():
        v = df[[c for c in cols if c in df.columns]].sum(axis=1) * scale
        out[f"{fuel}_heating_kwh"] = v
        space_fuel = space_fuel + v
        space_heat = space_heat + v * eff[fuel]
    for fuel, cols in dhw.items():
        v = df[[c for c in cols if c in df.columns]].sum(axis=1) * scale
        out[f"{fuel}_dhw_kwh"] = v
        dhw_fuel = dhw_fuel + v
        dhw_heat = dhw_heat + v * eff[fuel]
    out["space_heating_fuel_kwh"] = space_fuel
    out["dhw_fuel_kwh"] = dhw_fuel
    out["space_heating_kwh"] = space_heat
    out["dhw_kwh"] = dhw_heat
    out["heat_total_kwh"] = space_heat + dhw_heat
    return out


def _raw_path(dataset: str, puma: str, profile_type: str):
    return config.RAW / "nrel" / dataset / f"{puma}_{profile_type}.csv"


def load_profile(dataset: str, puma: str, profile_type: str) -> pd.DataFrame | None:
    """One building type in one PUMA -> hourly rows (hour-ending EST). None if absent."""
    path = _raw_path(dataset, puma, profile_type)
    if not path.exists():
        return None
    raw = pd.read_csv(path, parse_dates=["timestamp"])
    if dataset == "comstock":
        scale, basis = 1.0, "floor_area_sqft"
        scale_value = float(raw["floor_area_represented"].iloc[0])
        heat = _heat_columns(raw, COMSTOCK_SPACE_HEATING, COMSTOCK_DHW, scale)
    else:
        scale_value = float(raw["units_represented"].iloc[0])
        scale, basis = scale_value, "dwelling_units"   # per-unit values -> stock totals
        heat = _heat_columns(raw, RESSTOCK_SPACE_HEATING, RESSTOCK_DHW, scale)
    value_cols = [c for c in heat.columns if c != "timestamp"]
    hourly = timeutils.to_hourly(heat, value_cols)
    hourly.insert(1, "puma", puma)
    hourly.insert(2, "dataset", "ComStock" if dataset == "comstock" else "ResStock")
    hourly.insert(3, "profile_type", profile_type)
    hourly["models_used"] = int(raw["models_used"].iloc[0])
    hourly["scale_basis"] = basis
    hourly["scale_value"] = scale_value
    hourly["low_model_count"] = hourly["models_used"] < config.get("nrel.min_models_used")
    return hourly


def build_hourly_profiles(pumas: list[str] | None = None) -> pd.DataFrame:
    """All downloaded building types for the given PUMAs -> ``hourly_profiles``."""
    n = config.load_settings()["nrel"]
    pumas = pumas or [n["primary_puma"]]
    frames = []
    for puma in pumas:
        for ds, types in [("comstock", n["comstock_types"]), ("resstock", n["resstock_types"])]:
            for t in types:
                df = load_profile(ds, puma, t)
                if df is not None and df["heat_total_kwh"].sum() > 0:
                    frames.append(df)
    if not frames:
        raise FileNotFoundError("no NREL files found; run python scripts/download_nrel.py")
    out = pd.concat(frames, ignore_index=True)
    timeutils.check_hourly(out, by=["puma", "profile_type"])
    return out


def build_fuel_heat_fractions(pumas: list[str] | None = None) -> pd.DataFrame:
    """Annual share of each fuel used for space heating + hot water, per building type."""
    n = config.load_settings()["nrel"]
    pumas = pumas or [n["primary_puma"]]
    rows = []
    for puma in pumas:
        for ds, types in [("comstock", n["comstock_types"]), ("resstock", n["resstock_types"])]:
            space, dhw, total = ((COMSTOCK_SPACE_HEATING, COMSTOCK_DHW, COMSTOCK_FUEL_TOTAL)
                                 if ds == "comstock" else
                                 (RESSTOCK_SPACE_HEATING, RESSTOCK_DHW, RESSTOCK_FUEL_TOTAL))
            for t in types:
                path = _raw_path(ds, puma, t)
                if not path.exists():
                    continue
                raw = pd.read_csv(path)
                for fuel, cols in total.items():
                    tot = raw[[c for c in cols if c in raw]].to_numpy().sum()
                    sh = raw[[c for c in space.get(fuel, []) if c in raw]].to_numpy().sum()
                    dh = raw[[c for c in dhw.get(fuel, []) if c in raw]].to_numpy().sum()
                    if tot > 0:
                        rows.append({"puma": puma, "profile_type": t, "fuel": fuel,
                                     "fuel_total_kwh": tot, "space_heating_fuel_kwh": sh,
                                     "dhw_fuel_kwh": dh, "heat_fraction": (sh + dh) / tot})
    return pd.DataFrame(rows)
