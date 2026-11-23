"""OWNER: Emma. Load NREL ComStock + ResStock 15-min profiles -> ``hourly_profiles`` table.

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

from pathlib import Path

import pandas as pd

from heatreuse.config import load_settings
from heatreuse.io import write_table
from heatreuse.timeutils import check_hourly, to_hourly

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

RESSTOCK_PROFILE_TYPES = [
    "multi-family_with_2_-_4_units",
    "multi-family_with_5plus_units",
    "single-family_attached",
]

COMSTOCK_PROFILE_TYPES = [
    "fullservicerestaurant", "hospital", "largehotel", "largeoffice", "mediumoffice",
    "outpatient", "primaryschool", "quickservicerestaurant", "retailstandalone",
    "secondaryschool", "smallhotel", "smalloffice", "warehouse",
]

OUTPUT_COLS = [
    "timestamp", "puma", "dataset", "profile_type", "models_used", "scale_basis", "scale_value", 
    "natural_gas_heating_kwh", "fuel_oil_heating_kwh","propane_heating_kwh", "electricity_heating_kwh", 
    "district_heating_kwh", "space_heating_fuel_kwh", "dhw_fuel_kwh", "space_heating_kwh", "dhw_kwh", 
    "wood_dhw_kwh", "heat_total_kwh", "natural_gas_dhw_kwh", "fuel_oil_dhw_kwh",
    "propane_dhw_kwh", "district_dhw_kwh", "electricity_dhw_kwh", "low_model_count",
    "wood_heating_kwh", "natural_gas_total_kwh", "fuel_oil_total_kwh", "propane_total_kwh", "district_total_kwh",
    "electricity_total_kwh", "wood_total_kwh",  
]


def load_comstock(puma: str, profile_type: str) -> pd.DataFrame:
    """Read one raw ComStock file from data/raw/nrel/comstock/."""
    df = pd.read_csv(Path("data/raw/nrel/comstock") / f"{puma}_{profile_type}.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")


def load_resstock(puma: str, profile_type: str) -> pd.DataFrame:
    """Read one raw ResStock file from data/raw/nrel/resstock/. """
    df = pd.read_csv(Path("data/raw/nrel/resstock") / f"{puma}_{profile_type}.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")


def build_hourly_profiles(pumas: list[str] | None = None) -> pd.DataFrame:
    """Steps 1-7 above. Returns the ``hourly_profiles`` table. """

    settings = load_settings()

    pumas = pumas or [settings["nrel"]["primary_puma"]]

    to_load = [("ResStock", profile_type, load_resstock, RESSTOCK_SPACE_HEATING, RESSTOCK_DHW, RESSTOCK_FUEL_TOTAL, "dwelling_units", "units_represented")
                for profile_type in RESSTOCK_PROFILE_TYPES]

    to_load += [("ComStock", profile_type, load_comstock, COMSTOCK_SPACE_HEATING, COMSTOCK_DHW, COMSTOCK_FUEL_TOTAL, "floor_area_sqft", "floor_area_represented")
                 for profile_type in COMSTOCK_PROFILE_TYPES]

    datasets = []
    for puma in pumas:
        for dataset, profile_type, load_file, space_fields, dhw_fields, total_fields, scale_basis, size_col in to_load:
            df = load_file(puma, profile_type)

            scale_value = df[size_col].iloc[0]
            if dataset == "ResStock":
                scale = scale_value
            else:
                scale = 1

            space_cols = {}
            dhw_cols = {}

            hourly = pd.DataFrame(index = df.index)
            for fuel in FUELS:
                fuel_name = fuel.replace("_heating", "")
                for kind, fields in (("heating", space_fields), ("dhw", dhw_fields), ("total", total_fields)):
                    cols = fields.get(fuel, [])
                    col = f"{fuel_name}_{kind}_kwh"
                    hourly[col] = df.reindex(columns = cols, fill_value = 0).sum(axis=1) * scale

                    if kind == "heating":
                        space_cols[col] = fuel
                    elif kind == "dhw":
                        dhw_cols[col] = fuel 

            hourly["space_heating_fuel_kwh"] = hourly[list(space_cols)].sum(axis = 1)
            hourly["dhw_fuel_kwh"] = hourly[list(dhw_cols)].sum(axis=1)

            efficiencies = settings["heat"]["efficiency"]
            hourly["space_heating_kwh"] = sum(hourly[c] * efficiencies[f] for c, f in space_cols.items())
            hourly["dhw_kwh"] = sum(hourly[c] * efficiencies[f] for c, f in dhw_cols.items())
            hourly["heat_total_kwh"] = hourly["space_heating_kwh"] + hourly["dhw_kwh"]

            hourly = to_hourly(hourly.reset_index(), value_cols=list(hourly.columns))

            hourly["puma"] = puma
            hourly["dataset"] = dataset
            hourly["profile_type"] = profile_type
            hourly["models_used"] = df["models_used"].iloc[0]
            hourly["scale_basis"] = scale_basis
            hourly["scale_value"] = scale_value

            datasets.append(hourly)

    all_hourly = pd.concat(datasets, ignore_index=True)
    all_hourly["low_model_count"] = all_hourly["models_used"] < settings["nrel"]["min_models_used"]


    all_hourly = (all_hourly[OUTPUT_COLS].sort_values(["dataset", "puma", "profile_type", "timestamp"]).reset_index(drop = True))
    check_hourly(all_hourly, by=["puma", "profile_type"])
    return all_hourly

def build_fuel_heat_fractions(raw: pd.DataFrame) -> pd.DataFrame:
    """Step 8. Returns the ``fuel_heat_fractions`` table."""

    kwh_cols = [c for c in raw.columns if c.endswith("_kwh")]

    annual = raw.groupby(["puma", "profile_type"])[kwh_cols].sum()

    rows = []
    for (puma, label), a in annual.iterrows():
        for fuel in FUELS:
            fuel_name = fuel.replace("_heating", "")
            total = a[f"{fuel_name}_total_kwh"]
            if total <= 0:
                continue
            space = a[f"{fuel_name}_heating_kwh"]
            dhw = a[f"{fuel_name}_dhw_kwh"]
            rows.append({"puma": puma, "profile_type": label, "fuel": fuel, "fuel_total_kwh": total,
                                 "space_heating_fuel_kwh": space, "dhw_fuel_kwh": dhw, "heat_fraction": (space + dhw) / total})  
    
    
    return pd.DataFrame(rows)
    
if __name__ == "__main__":
    hourly_profiles = build_hourly_profiles()

    write_table(hourly_profiles, "hourly_profiles")
    write_table(build_fuel_heat_fractions(hourly_profiles), "fuel_heat_fractions")
