"""OWNER: Rafa. Clean LL84 -> ``ll84_clean`` with the annual heat target.

LL84 column names below come from the Week 2 plan / Socrata dataset 5zyy-y8am. They
could not be checked from the cloud sandbox: confirm against the downloaded header and
fix RENAME before writing code that depends on it.

Target (decisions D1, D2, D11):
    estimated_annual_heat_kwh =
        kbtu_to_kwh( gas_kbtu   * heat_fraction_gas(profile_type) * eff_gas
                   + oil_kbtu   * heat_fraction_oil(profile_type) * eff_oil
                   + steam_kbtu * eff_district            # see note
                   + dhw_kbtu   * eff_district )
    heat_fraction_* comes from Emma's ``fuel_heat_fractions`` table (local, per building
    type) with the EIA national figures as fallback (gas: 0.69 commercial, 0.68 residential).
    Steam note: some Manhattan buildings run steam absorption chillers in summer, so
    steam is not all heat. Use the ComStock district_heating heat fraction the same way.

Steps (Week 2 plan, kept):
  1. Filter calendar_year == settings.project.ll84_calendar_year; dedupe Property ID.
  2. Strip commas, "Not Available" -> NaN, keep a reported 0 as 0.
  3. Flag invalid area, negative use, meter gaps/overlaps, estimated values.
  4. gas_only_proxy_kwh (simple baseline target).
  5. Composite target as above; sensitivity: +/-10% on efficiencies and fractions.
  6. Missing-fuel rule: treat a fuel as absent (0) only if the property reports
     total site energy and the other fuels explain it within 10%; otherwise flag
     label_quality_flag = "incomplete". Report how many rows survive.
Output units: raw fuel columns stay *_kbtu, all heat columns are *_kwh (D3).
"""

from __future__ import annotations

import pandas as pd

RENAME = {
    "Property ID": "property_id",
    "NYC Borough, Block and Lot (BBL)": "bbl",
    "NYC Building Identification Number (BIN)": "bin",
    "Calendar Year": "calendar_year",
    "Largest Property Use Type": "property_type",
    "Property GFA - Self-Reported (ft²)": "building_floor_area_sqft",
    "Parent Property Id": "parent_property_id",
    "Number of Buildings": "number_of_buildings",
    "Natural Gas Use (kBtu)": "natural_gas_kbtu",
    "District Steam Use (kBtu)": "steam_kbtu",
    "District Hot Water Use (kBtu)": "district_hot_water_kbtu",
    "Fuel Oil #1 Use (kBtu)": "fuel_oil_1_kbtu",
    "Fuel Oil #2 Use (kBtu)": "fuel_oil_2_kbtu",
    "Fuel Oil #4 Use (kBtu)": "fuel_oil_4_kbtu",
    "Fuel Oil #5 & 6 Use (kBtu)": "fuel_oil_5_6_kbtu",
    "Electricity Use - Grid Purchase (kWh)": "electricity_kwh",
    "Latitude": "latitude",
    "Longitude": "longitude",
}
MISSING_TOKENS = ["Not Available", "Not Applicable", "", "N/A"]
EIA_GAS_HEAT_FRACTION = {"commercial": 0.69, "residential": 0.68}

QUALITY_FLAGS = ["ok", "incomplete", "invalid_area", "negative_use", "estimated",
                 "meter_gap", "outlier"]


def load_raw(path=None) -> pd.DataFrame:
    """TODO(Rafa): read data/raw/nyc/ll84.csv, apply RENAME."""
    raise NotImplementedError


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Steps 1-3. TODO(Rafa)."""
    raise NotImplementedError


def build_target(clean_df: pd.DataFrame, fractions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Steps 4-6 -> ``ll84_clean``. TODO(Rafa)."""
    raise NotImplementedError
