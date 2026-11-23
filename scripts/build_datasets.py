"""Build the ready-to-model datasets in data/modeling/ (already committed: you don't need to
run this unless the source data or the heat definition changes).

    python scripts/download_nrel.py && python scripts/build_datasets.py --hourly
    python scripts/build_datasets.py --buildings    # needs data/raw/nyc/ll84_2024.csv + pluto.csv

Outputs:
    data/modeling/hourly_heat.parquet            Track A (hourly demand by building type)
    data/modeling/building_heat_train.parquet    Track B (LL84 buildings, annual heat target)
    data/modeling/building_heat_predict.parquet  Track B application set (lots near 111 8th Ave)
    data/modeling/fuel_heat_fractions.csv        heating share of each fuel by building type
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from heatreuse import config
from heatreuse.forecasting import features, profiles, weather

OUT = ROOT / "data" / "modeling"
HOURLY_DROP_TYPES = {"mobile_home", "single-family_detached"}  # ~absent in Manhattan, 1-5 models
HOURLY_COLS = ["timestamp", "timestamp_local", "profile_type", "dataset", "models_used",
               "low_model_count", "scale_basis", "scale_value",
               "heat_total_kwh", "space_heating_kwh", "dhw_kwh", "heat_intensity",
               "temp_c", "rel_humidity_pct", "wind_speed_ms", "ghi_wm2", "hdh_18c",
               "temp_c_roll24", "temp_c_lag1", "temp_c_lag3",
               "hour_of_day", "day_of_week", "month", "is_weekend", "is_holiday", "data_split"]


def build_hourly() -> None:
    p = profiles.build_hourly_profiles()
    f = features.build_features(p, weather.build_weather_hourly())
    f = f[~f["profile_type"].isin(HOURLY_DROP_TYPES)][HOURLY_COLS]
    f.to_parquet(OUT / "hourly_heat.parquet", index=False)
    profiles.build_fuel_heat_fractions().to_csv(OUT / "fuel_heat_fractions.csv", index=False)
    print(f"hourly_heat: {len(f):,} rows, {f['profile_type'].nunique()} building types")


def build_buildings() -> None:
    from heatreuse.heat_demand import building_dataset as bd
    fr = profiles.build_fuel_heat_fractions()
    min_models = config.get("nrel.min_models_used")
    p = profiles.build_hourly_profiles()
    low = set(p.loc[p["models_used"] < min_models, "profile_type"])
    ll = bd.build_target(bd.clean_ll84(), fr, low)
    lots = bd.lot_features(bd.load_pluto())
    train, report = bd.build_train(ll, lots)
    train.to_parquet(OUT / "building_heat_train.parquet", index=False)
    pred = bd.build_predict(lots, train, bd.property_lot_map(ll))
    pred.to_parquet(OUT / "building_heat_predict.parquet", index=False)
    report["predict_lots_2km"] = len(pred)
    report["predict_lots_1km"] = int(pred["within_1000m"].sum())
    (OUT / "building_build_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hourly", action="store_true")
    ap.add_argument("--buildings", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.hourly or not a.buildings:
        build_hourly()
    if a.buildings or not a.hourly:
        build_buildings()
