# Builds hourly heating table for PUMA G36003807 from NREL ComStock and ResStock

import pandas as pd
import numpy as np
from pathlib import Path

resstock_folder = Path("data/resstock")
comstock_folder = Path("data/comstock")
output_folder = Path("outputs")
puma = "G36003807"
FIRST_HOUR = pd.Timestamp("2018-01-01 01:00")
LAST_HOUR = pd.Timestamp("2019-01-01 00:00")


resstock_types = {
    "g36003807-multi-family_with_2_-_4_units.csv": "multi_2_4_units",
    "g36003807-multi-family_with_5plus_units.csv": "multi_5plus_units",
    "g36003807-single-family_attached.csv": "single_family_attached",
}
comstock_types = {
    "up0-g36003807-fullservicerestaurant.csv": "full_service_restaurant",
    "up0-g36003807-hospital.csv": "hospital",
    "up0-g36003807-largehotel.csv": "large_hotel",
    "up0-g36003807-largeoffice.csv": "large_office",
    "up0-g36003807-mediumoffice.csv": "medium_office",
    "up0-g36003807-outpatient.csv": "outpatient",
    "up0-g36003807-primaryschool.csv": "primary_school",
    "up0-g36003807-quickservicerestaurant.csv": "quick_service_restaurant",
    "up0-g36003807-retailstandalone.csv": "retail_standalone",
    "up0-g36003807-secondaryschool.csv": "secondary_school",
    "up0-g36003807-smallhotel.csv": "small_hotel",
    "up0-g36003807-smalloffice.csv": "small_office",
    "up0-g36003807-warehouse.csv": "warehouse",
}

# renaming fields to output names
resstock_fields = {
    "out.electricity.fans_heating.energy_consumption": "fans_heating_kwh",
    "out.electricity.heating.energy_consumption": "electricity_heating_kwh",
    "out.electricity.heating_supplement.energy_consumption": "electricity_heating_supplement_kwh",
    "out.electricity.hot_tub_heater.energy_consumption": "hot_tub_heating_kwh",
    "out.electricity.pumps_heating.energy_consumption": "pumps_heating_kwh",
    "out.fuel_oil.heating.energy_consumption": "fuel_oil_heating_kwh",
    "out.natural_gas.heating.energy_consumption": "natural_gas_heating_kwh",
    "out.propane.heating.energy_consumption": "propane_heating_kwh",
}

comstock_fields = {
    "out.natural_gas.heating.energy_consumption.kwh": "natural_gas_heating_kwh",
    "out.fuel_oil.heating.energy_consumption.kwh": "fuel_oil_heating_kwh",
    "out.district_heating.heating.energy_consumption.kwh": "district_heating_kwh",
    "out.electricity.heating.energy_consumption.kwh": "electricity_heating_kwh",
    "out.propane.heating.energy_consumption.kwh": "propane_heating_kwh",
    "out.district_heating.water_systems.energy_consumption.kwh": "water_systems_kwh",
}

# columns that count as space heating
total_cols = [
    "electricity_heating_kwh",
    "electricity_heating_supplement_kwh",
    "natural_gas_heating_kwh", 
    "fuel_oil_heating_kwh",
    "propane_heating_kwh", 
    "district_heating_kwh",
]

output_cols = [
    "timestamp_hour", "puma", "dataset", "building_type", "natural_gas_heating_kwh", "fuel_oil_heating_kwh",
    "propane_heating_kwh", "electricity_heating_kwh", "electricity_heating_supplement_kwh", "district_heating_kwh",
    "space_heating_total_kwh", "space_heating_total_scaled_kwh", "values_are_per_unit", "fans_heating_kwh", 
    "pumps_heating_kwh", "water_systems_kwh", "hot_tub_heating_kwh", "models_used", "units_represented", 
    "floor_area_represented",
]

# loads one 15 minute file and returns hourly table
def load_hourly (path, fields, dataset, label, size_col):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")

    cols = [c for c in fields if c in df.columns]
    if df[cols].isna().any().any():
        print(f"Warning: {label} has NaN values in raw data")
    

    hourly = (df.reindex(columns = list(fields), fill_value = 0).resample("h", closed = "right", label = "right").sum().rename(columns = fields))
    hourly["building_type"] = label
    hourly["dataset"] = dataset
    hourly["models_used"] = df["models_used"].iloc[0]
    hourly[size_col] = df[size_col].iloc[0]

    return hourly

# checks the table
def check(hourly_table):
    problems = []

    for building_type, rows in hourly_table.groupby("building_type"):
        hours = rows["timestamp_hour"]

        if len(rows) != 8760:
            problems.append(f"{building_type}: has {len(rows)} rows, expected 8760")

        if hours.duplicated().any():
            problems.append(f"{building_type}: has duplicate hours")

        if hours.min() != FIRST_HOUR:
            problems.append(f"{building_type}: first hour is {hours.min()}, expected {FIRST_HOUR}")

        if hours.max() != LAST_HOUR:
            problems.append(f"{building_type}: last hour is {hours.max()}, expected {LAST_HOUR}")
        
    energy_cols = [col for col in hourly_table.columns if col.endswith("_kwh")]
    energy_vals = hourly_table[energy_cols]

    if (energy_vals < 0).any().any():
        problems.append("some energy (_kwh) values are negative")

    if problems:
        print("Problems: ")
        for p in problems:
            print(" -", p)
    else:
        print("Check passed: 8760 hours per building type, no duplicates, no negatives.")

# loads every file
datasets = []

for filename, label in resstock_types.items():
    datasets.append(load_hourly(resstock_folder / filename, resstock_fields, "ResStock", label, "units_represented"))

for filename, label in comstock_types.items():
    datasets.append(load_hourly(comstock_folder / filename, comstock_fields, "ComStock", label, "floor_area_represented"))


all_hourly = pd.concat(datasets)

# fills the energy columns that only exist for one dataset
kwh_cols = [c for c in all_hourly.columns if c.endswith("_kwh")]
all_hourly[kwh_cols] = all_hourly[kwh_cols].fillna(0)

# totals
all_hourly["space_heating_total_kwh"] = all_hourly[total_cols].sum(axis = 1)

# scale ResStock by units represented to mach aggregates like ComStock
res = all_hourly["dataset"] == "ResStock"
all_hourly["values_are_per_unit"] = res
scale = np.where(res, all_hourly["units_represented"], 1)
all_hourly["space_heating_total_scaled_kwh"] = all_hourly["space_heating_total_kwh"] * scale

# put index in column and add puma
all_hourly = all_hourly.reset_index().rename(columns = {"timestamp": "timestamp_hour"})
all_hourly["puma"] = puma

all_hourly = (all_hourly[output_cols].sort_values(["dataset", "building_type", "timestamp_hour"]).reset_index(drop = True))

check(all_hourly)

output_folder.mkdir(exist_ok = True)
all_hourly.to_parquet(output_folder / "hourly_heat.parquet", index = False)
all_hourly.to_csv(output_folder / "hourly_heat.csv", index = False)
print(f"Saved {len(all_hourly):,} rows to {output_folder}/")


