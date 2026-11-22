# Identifies that the kwh values are per unit in ResStock

import pandas as pd
from pathlib import Path

meta = pd.read_parquet("metadata.parquet")
resstock_folder = Path("data/resstock")

heat_cols = [
    "out.electricity.fans_heating.energy_consumption",
        "out.electricity.heating.energy_consumption",
        "out.electricity.heating_supplement.energy_consumption",
        "out.fuel_oil.heating.energy_consumption",
        "out.natural_gas.heating.energy_consumption",
        "out.propane.heating.energy_consumption",
]

checks = {
    "Single-Family Attached": "g36003807-single-family_attached.csv",
    "Multi-Family with 2 - 4 Units": "g36003807-multi-family_with_2_-_4_units.csv",
    "Multi-Family with 5+ Units": "g36003807-multi-family_with_5plus_units.csv",
}

for label, filename in checks.items():
    homes = meta[(meta["in.nhgis_puma_gisjoin"] == "G36003807") &
                 (meta["in.geometry_building_type_recs"] == label)]
    per_home = homes[heat_cols].sum(axis = 1)

    aggregate = pd.read_csv(resstock_folder / filename)
    agg_total = aggregate[heat_cols].sum().sum()

    print(label)
    print(" Home: ", len(homes))
    print(" Mean per home: ", round(per_home.mean(), 1))
    print(" Sum of homes: ", round(per_home.sum(), 1))
    print(" Aggregate CSV: ", round(agg_total, 1))