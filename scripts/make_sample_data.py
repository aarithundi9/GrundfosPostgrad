"""Write SYNTHETIC contract tables to data/sample/ so downstream work (Pod 3, map) can
start before upstream tables exist. Numbers are fake; shapes and columns are real.

    python scripts/make_sample_data.py
    HEATREUSE_PROCESSED=data/sample python scripts/run_pipeline.py ...   # use them
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["HEATREUSE_PROCESSED"] = "data/sample"
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from heatreuse import config, io, timeutils
from heatreuse.crosswalk import valid_profile_types
from heatreuse.forecasting.shares import normalize
from heatreuse.matching.datacenter_heat import build_datacenter_heat


def fake_shares(rng) -> pd.DataFrame:
    ts = timeutils.canonical_index(2018)
    doy = (ts - pd.Timedelta(hours=1)).dayofyear.to_numpy()
    hour = (ts - pd.Timedelta(hours=1)).hour.to_numpy()
    temp = 12.5 - 11 * np.cos(2 * np.pi * (doy - 20) / 365) + 4 * np.sin(2 * np.pi * (hour - 9) / 24)
    hdh = np.clip(18.3 - temp, 0, None)
    rows = []
    for p in sorted(valid_profile_types()):
        occ = 1 + 0.4 * ((hour >= 6) & (hour <= 18))  # crude occupancy bump
        dhw = 0.15 * occ
        v = hdh * occ * rng.uniform(0.8, 1.2) + dhw * hdh.mean()
        rows.append(pd.DataFrame({"profile_type": p, "source": "simulated_2018",
                                  "timestamp": ts, "hourly_share": normalize(v)}))
    return pd.concat(rows, ignore_index=True)


def fake_buildings(rng, n=150) -> pd.DataFrame:
    lat0, lon0 = 40.7411, -74.0034
    r = 1000 * np.sqrt(rng.uniform(0, 1, n))
    th = rng.uniform(0, 2 * np.pi, n)
    lat = lat0 + (r * np.cos(th)) / 111_000
    lon = lon0 + (r * np.sin(th)) / (111_000 * np.cos(np.radians(lat0)))
    types = rng.choice(["multi-family_with_5plus_units", "largeoffice", "mediumoffice",
                        "smallhotel", "retailstandalone", "secondaryschool"], n,
                       p=[0.5, 0.15, 0.15, 0.05, 0.1, 0.05])
    area = np.exp(rng.normal(np.log(60_000), 0.8, n)).round()
    res_share = np.where(types == "multi-family_with_5plus_units", 1.0, rng.uniform(0, 0.4, n))
    heat_kwh = area * rng.uniform(15, 35, n)  # ~15-35 kWh/sqft/yr
    reported = rng.uniform(size=n) < 0.4
    return pd.DataFrame({
        "dc_id": "dc_111_8th_ave", "bin": [f"1{100000 + i:06d}" for i in range(n)],
        "bbl": [f"10{rng.integers(0, 10**8):08d}" for _ in range(n)],
        "distance_m": r.round(1), "in_radius": True, "bldgarea": area,
        "profile_type": types, "res_share": res_share.round(2), "com_share": (1 - res_share).round(2),
        "heat_source": np.where(reported, "reported", "predicted"),
        "heat_simple_kwh": heat_kwh * rng.uniform(0.8, 1.2, n), "heat_model_kwh": heat_kwh,
        "annual_heat_kwh": heat_kwh, "latitude": lat, "longitude": lon, "is_synthetic": True,
    })


def main() -> None:
    rng = np.random.default_rng(42)
    io.write_table(fake_shares(rng), "hourly_shares")
    io.write_table(fake_buildings(rng), "study_area_buildings")
    io.write_table(build_datacenter_heat(), "datacenter_heat_hourly")
    print(f"wrote synthetic tables to {config.PROCESSED}")


if __name__ == "__main__":
    main()
