# Builds hourly heating table and fuel_heat_fractions for PUMA G36003807 from NREL ComStock and ResStock

import pandas as pd
import numpy as np
from pathlib import Path

resstock_folder = Path("data/resstock")
comstock_folder = Path("data/comstock")
output_folder = Path("data/processed")
puma = "G36003807"
FIRST_HOUR = pd.Timestamp("2018-01-01 01:00")
LAST_HOUR = pd.Timestamp("2019-01-01 00:00")
MIN_MODELS_USED = 10

# fuel heat efficiencies
efficiencies = {
    "natural_gas": 0.80,
    "fuel_oil": 0.80,
    "propane": 0.80,
    "district": 1.00,
    "electricity": 1.00,
}

resstock_types = {
    "g36003807-multi-family_with_2_-_4_units.csv": "multi-family_with_2_-_4_units",
    "g36003807-multi-family_with_5plus_units.csv": "multi-family_with_5plus_units",
    "g36003807-single-family_attached.csv": "single-family_attached",
}
comstock_types = {
    "up0-g36003807-fullservicerestaurant.csv": "fullservicerestaurant",
    "up0-g36003807-hospital.csv": "hospital",
    "up0-g36003807-largehotel.csv": "largehotel",
    "up0-g36003807-largeoffice.csv": "largeoffice",
    "up0-g36003807-mediumoffice.csv": "mediumoffice",
    "up0-g36003807-outpatient.csv": "outpatient",
    "up0-g36003807-primaryschool.csv": "primaryschool",
    "up0-g36003807-quickservicerestaurant.csv": "quickservicerestaurant",
    "up0-g36003807-retailstandalone.csv": "retailstandalone",
    "up0-g36003807-secondaryschool.csv": "secondaryschool",
    "up0-g36003807-smallhotel.csv": "smallhotel",
    "up0-g36003807-smalloffice.csv": "smalloffice",
    "up0-g36003807-warehouse.csv": "warehouse",
}

# renaming fields to output names
resstock_fields = {
    "out.electricity.fans_heating.energy_consumption": "fans_heating_kwh",
    "out.electricity.heating.energy_consumption": "electricity_heating_kwh",
    "out.electricity.heating_supplement.energy_consumption": "electricity_heating_supplement_kwh",
    "out.electricity.pumps_heating.energy_consumption": "pumps_heating_kwh",
    "out.fuel_oil.heating.energy_consumption": "fuel_oil_heating_kwh",
    "out.natural_gas.heating.energy_consumption": "natural_gas_heating_kwh",
    "out.propane.heating.energy_consumption": "propane_heating_kwh",
    "out.electricity.water_systems.energy_consumption": "electricity_dhw_kwh",
    "out.fuel_oil.water_systems.energy_consumption": "fuel_oil_dhw_kwh",
    "out.natural_gas.water_systems.energy_consumption": "natural_gas_dhw_kwh",
    "out.propane.water_systems.energy_consumption": "propane_dhw_kwh",
    "out.propane.total.energy_consumption": "propane_total_kwh",
    "out.electricity.total.energy_consumption": "electricity_total_kwh",
    "out.fuel_oil.total.energy_consumption": "fuel_oil_total_kwh",
    "out.natural_gas.total.energy_consumption": "natural_gas_total_kwh",
}

comstock_fields = {
    "out.natural_gas.heating.energy_consumption.kwh": "natural_gas_heating_kwh",
    "out.fuel_oil.heating.energy_consumption.kwh": "fuel_oil_heating_kwh",
    "out.district_heating.heating.energy_consumption.kwh": "district_heating_kwh",
    "out.electricity.heating.energy_consumption.kwh": "electricity_heating_kwh",
    "out.propane.heating.energy_consumption.kwh": "propane_heating_kwh",
    "out.district_heating.water_systems.energy_consumption.kwh": "district_dhw_kwh",
    "out.electricity.water_systems.energy_consumption.kwh": "electricity_dhw_kwh",
    "out.natural_gas.water_systems.energy_consumption.kwh": "natural_gas_dhw_kwh",
    "out.propane.water_systems.energy_consumption.kwh": "propane_dhw_kwh",
    "out.fuel_oil.water_systems.energy_consumption.kwh": "fuel_oil_dhw_kwh",
    "out.district_heating.total.energy_consumption.kwh": "district_total_kwh",
    "out.electricity.total.energy_consumption.kwh": "electricity_total_kwh",
    "out.fuel_oil.total.energy_consumption.kwh": "fuel_oil_total_kwh",
    "out.natural_gas.total.energy_consumption.kwh": "natural_gas_total_kwh",
    "out.propane.total.energy_consumption.kwh": "propane_total_kwh",
}

# maps each space heating column to its fuel
space_cols = {
    "electricity_heating_kwh": "electricity",
    "electricity_heating_supplement_kwh": "electricity",
    "natural_gas_heating_kwh": "natural_gas", 
    "fuel_oil_heating_kwh": "fuel_oil",
    "propane_heating_kwh": "propane", 
    "district_heating_kwh": "district",
}

# maps each domestic hot water column to its fuel
dhw_cols = {
    "natural_gas_dhw_kwh": "natural_gas",
    "fuel_oil_dhw_kwh": "fuel_oil", 
    "propane_dhw_kwh": "propane",
    "district_dhw_kwh": "district",
    "electricity_dhw_kwh": "electricity",
}

# columns for each fuel group for fuel_heat_fractions
fuel_groups = {
    "natural_gas": (["natural_gas_heating_kwh"], ["natural_gas_dhw_kwh"], "natural_gas_total_kwh"),
    "fuel_oil": (["fuel_oil_heating_kwh"], ["fuel_oil_dhw_kwh"], "fuel_oil_total_kwh"),
    "propane": (["propane_heating_kwh"], ["propane_dhw_kwh"], "propane_total_kwh"),
    "district": (["district_heating_kwh"], ["district_dhw_kwh"], "district_total_kwh"),
    "electricity": (["electricity_heating_kwh", "electricity_heating_supplement_kwh"], ["electricity_dhw_kwh"], "electricity_total_kwh"),
}

# output columns
output_cols = [
    "timestamp", "puma", "dataset", "profile_type", "models_used", "scale_basis", "scale_value", 
    "natural_gas_heating_kwh", "fuel_oil_heating_kwh","propane_heating_kwh", "electricity_heating_kwh", 
    "electricity_heating_supplement_kwh", "district_heating_kwh",
    "space_heating_fuel_kwh", "fans_heating_kwh", "pumps_heating_kwh",
    "dhw_fuel_kwh", "space_heating_kwh", "dhw_kwh", "heat_total_kwh", "natural_gas_dhw_kwh", "fuel_oil_dhw_kwh",
    "propane_dhw_kwh", "district_dhw_kwh", "electricity_dhw_kwh", "low_model_count" 
]

# loads one 15 minute file and returns hourly table
def load_hourly (path, fields, dataset, label, size_col, scale_basis):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")

    missing = [c for c in fields if c not in df.columns]
    if missing:
        print(f"Warning: {label} missing columns (filled with 0): {missing}")

    hourly = (df.reindex(columns = list(fields), fill_value = 0).resample("h", closed = "right", label = "right").sum().rename(columns = fields))
    hourly["profile_type"] = label
    hourly["dataset"] = dataset
    hourly["models_used"] = df["models_used"].iloc[0]
    hourly["scale_basis"] = scale_basis
    hourly["scale_value"] = df[size_col].iloc[0]

    return hourly

# checks the table
def check(hourly_table):
    problems = []

    for profile_type, rows in hourly_table.groupby("profile_type"):
        hours = rows["timestamp"]

        if len(rows) != 8760:
            problems.append(f"{profile_type}: has {len(rows)} rows, expected 8760")

        if hours.duplicated().any():
            problems.append(f"{profile_type}: has duplicate hours")

        if hours.min() != FIRST_HOUR:
            problems.append(f"{profile_type}: first hour is {hours.min()}, expected {FIRST_HOUR}")

        if hours.max() != LAST_HOUR:
            problems.append(f"{profile_type}: last hour is {hours.max()}, expected {LAST_HOUR}")
        
    energy_cols = [col for col in hourly_table.columns if col.endswith("_kwh")]
    energy_vals = hourly_table[energy_cols]

    if (energy_vals < 0).any().any():
        problems.append("some energy (_kwh) values are negative")

    if problems:
        print("Problems: ")
        for p in problems:
            print(" -", p)
    else:
        print("Check passed: 8760 hours per profile type, no duplicates, no negatives.")

# loads every file
datasets = []

for filename, label in resstock_types.items():
    datasets.append(load_hourly(resstock_folder / filename, resstock_fields, "ResStock", label, "units_represented", "units"))

for filename, label in comstock_types.items():
    datasets.append(load_hourly(comstock_folder / filename, comstock_fields, "ComStock", label, "floor_area_represented", "floor_area"))


all_hourly = pd.concat(datasets)

# fills the energy columns that only exist for one dataset
kwh_cols = [c for c in all_hourly.columns if c.endswith("_kwh")]
all_hourly[kwh_cols] = all_hourly[kwh_cols].fillna(0)

# scale ResStock by multiplying every _kwh column by units_represented so all values are totals like ComStock
res = all_hourly["dataset"] == "ResStock"
all_hourly.loc[res, kwh_cols] = all_hourly.loc[res, kwh_cols].mul(all_hourly.loc[res, "scale_value"], axis = 0)

# fuel consumed for space heating and DHW before efficiency
all_hourly["space_heating_fuel_kwh"] = all_hourly[list(space_cols)].sum(axis = 1)
all_hourly["dhw_fuel_kwh"] = all_hourly[list(dhw_cols)].sum(axis = 1)

# delivered heating = fuel consumed * efficiency
all_hourly["space_heating_kwh"] = sum (all_hourly[c] * efficiencies[f] for c, f in space_cols.items())
all_hourly["dhw_kwh"] = sum(all_hourly[c] * efficiencies[f] for c, f in dhw_cols.items())
all_hourly["heat_total_kwh"] = all_hourly["space_heating_kwh"] + all_hourly["dhw_kwh"]

# flags any model counts below min models used
all_hourly["low_model_count"] = all_hourly["models_used"] < MIN_MODELS_USED

# put index in column and add puma
all_hourly = all_hourly.reset_index()
all_hourly["puma"] = puma

# annual total of every _kwh column for each profile type
annual = all_hourly.groupby("profile_type")[kwh_cols].sum()

# finds fuel fractions by (dhw fuel + space heating fuel)/(total fuel)
rows = []
for p_type, a in annual.iterrows():
    for fuel, (s_cols, d_cols, total_col) in fuel_groups.items():
        if a[total_col] <= 0:
            continue
        space, dhw = a[s_cols].sum(), a[d_cols].sum()
        rows.append({"puma": puma, "profile_type": p_type, "fuel": fuel, "fuel_total_kwh": a[total_col],
                     "space_heating_fuel_kwh": space, "dhw_fuel_kwh": dhw, "heat_fraction": (space + dhw) / a[total_col]})

fuel_fractions = pd.DataFrame(rows)

# only keeps the output_cols we want and sorts by dataset, then profile_type, then timestamp
all_hourly = (all_hourly[output_cols].sort_values(["dataset", "profile_type", "timestamp"]).reset_index(drop = True))

check(all_hourly)

#try: 
    #from heatreuse.io import write_table
    #write_table(all_hourly, "hourly_profiles")
    #write_table(fuel_fractions, "fuel_heat_fractions")
#except ImportError:
    
output_folder.mkdir(parents = True, exist_ok = True)
all_hourly.to_parquet(output_folder / "hourly_profiles.parquet", index = False)
fuel_fractions.to_parquet(output_folder / "fuel_heat_fractions.parquet", index = False)
print(f"Saved {len(all_hourly):,} hourly rows and {len(fuel_fractions)} fraction rows to {output_folder}/")




