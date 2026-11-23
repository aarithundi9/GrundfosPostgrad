"""Score a model's predictions on the fixed test set. Same rules for everyone.

    python scripts/score.py hourly    submissions/<name>_hourly.csv
    python scripts/score.py buildings submissions/<name>_buildings.csv

Hourly file columns:    timestamp, profile_type, predicted_kwh
    one row per test hour (Oct-Dec 2018) per building type = 37,536 rows
Buildings file columns: property_id, predicted_heat_kwh
    one row per test building (split == "test" and label_quality_flag == "ok")

Adds your result to submissions/leaderboard.csv (lower is better for every metric).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from heatreuse import metrics

DATA = ROOT / "data" / "modeling"
BOARD = ROOT / "submissions" / "leaderboard.csv"


def hourly_truth() -> pd.DataFrame:
    d = pd.read_parquet(DATA / "hourly_heat.parquet")
    return d[d["data_split"] == "test"][["timestamp", "profile_type", "heat_total_kwh"]]


def buildings_truth() -> pd.DataFrame:
    d = pd.read_parquet(DATA / "building_heat_train.parquet")
    d = d[(d["split"] == "test") & (d["label_quality_flag"] == "ok")]
    return d[["property_id", "annual_heat_kwh", "bldgarea"]]


def score_hourly(pred: pd.DataFrame) -> dict:
    truth = hourly_truth()
    pred = pred.assign(timestamp=pd.to_datetime(pred["timestamp"]))
    m = truth.merge(pred, on=["timestamp", "profile_type"], how="left")
    if m["predicted_kwh"].isna().any():
        raise SystemExit(f"{int(m['predicted_kwh'].isna().sum())} test rows have no prediction")
    per_type = {t: metrics.score(g["heat_total_kwh"], g["predicted_kwh"])
                for t, g in m.groupby("profile_type")}
    pt = pd.DataFrame(per_type).T
    print(pt[["cvrmse", "nmbe", "wape"]].round(3).to_string())
    return {"primary_metric": "mean_cvrmse", "score": pt["cvrmse"].mean(),
            "mean_wape": pt["wape"].mean(), "mean_abs_nmbe": pt["nmbe"].abs().mean()}


def score_buildings(pred: pd.DataFrame) -> dict:
    truth = buildings_truth()
    pred = pred.assign(property_id=pred["property_id"].astype(str))
    m = truth.merge(pred, on="property_id", how="left")
    if m["predicted_heat_kwh"].isna().any():
        raise SystemExit(f"{int(m['predicted_heat_kwh'].isna().sum())} test buildings have no prediction")
    y, p = m["annual_heat_kwh"].to_numpy(), m["predicted_heat_kwh"].to_numpy()
    ape = np.abs(p - y) / y
    bands = pd.cut(m["bldgarea"], [0, 25e3, 50e3, 100e3, np.inf], labels=["<25k", "25-50k", "50-100k", "100k+"])
    print(pd.Series(ape).groupby(bands.to_numpy(), observed=True).median().round(3).rename("median_ape_by_size").to_string())
    return {"primary_metric": "median_ape", "score": float(np.median(ape)),
            "mae_kwh": metrics.mae(y, p), "wape": metrics.wape(y, p)}


def main() -> None:
    track, path = sys.argv[1], Path(sys.argv[2])
    pred = pd.read_csv(path, dtype={"property_id": str})
    res = score_hourly(pred) if track == "hourly" else score_buildings(pred)
    row = {"submitted": datetime.now().strftime("%Y-%m-%d %H:%M"), "track": track,
           "file": path.name, **{k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in res.items()}}
    print("\n", row)
    board = pd.concat([pd.read_csv(BOARD), pd.DataFrame([row])]) if BOARD.exists() else pd.DataFrame([row])
    board = board.drop_duplicates(["track", "file"], keep="last").sort_values(["track", "score"])
    board.to_csv(BOARD, index=False)


if __name__ == "__main__":
    main()
