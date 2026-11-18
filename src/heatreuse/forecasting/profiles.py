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

import pandas as pd

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


def load_comstock(puma: str, profile_type: str) -> pd.DataFrame:
    """Read one raw ComStock file from data/raw/nrel/comstock/. TODO(Emma)."""
    raise NotImplementedError


def load_resstock(puma: str, profile_type: str) -> pd.DataFrame:
    """Read one raw ResStock file from data/raw/nrel/resstock/. TODO(Emma)."""
    raise NotImplementedError


def build_hourly_profiles(pumas: list[str] | None = None) -> pd.DataFrame:
    """Steps 1-7 above. Returns the ``hourly_profiles`` table. TODO(Emma)."""
    raise NotImplementedError


def build_fuel_heat_fractions(raw: pd.DataFrame) -> pd.DataFrame:
    """Step 8. Returns the ``fuel_heat_fractions`` table. TODO(Emma)."""
    raise NotImplementedError
