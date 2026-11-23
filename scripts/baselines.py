"""Reference baselines every model should beat. Writes submissions/baseline_*.csv.

Hourly: per building type and hour-of-day/weekend, heat = a + b * heating degree-hours (fit on Jan-Sep).
Buildings: annual heat = PLUTO bldgarea x median kWh/sqft of training buildings of the same type.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, SUB = ROOT / "data" / "modeling", ROOT / "submissions"

h = pd.read_parquet(DATA / "hourly_heat.parquet")
out = []
for (t, hr, wk), g in h.groupby(["profile_type", "hour_of_day", "is_weekend"]):
    tr, te = g[g.data_split == "train"], g[g.data_split == "test"]
    b, a = np.polyfit(tr["hdh_18c"], tr["heat_total_kwh"], 1)
    out.append(pd.DataFrame({"timestamp": te["timestamp"], "profile_type": t,
                             "predicted_kwh": np.clip(a + b * te["hdh_18c"], 0, None)}))
pd.concat(out).to_csv(SUB / "baseline_hourly.csv", index=False)

b = pd.read_parquet(DATA / "building_heat_train.parquet")
ok = b[b.label_quality_flag == "ok"]
tr, te = ok[ok.split == "train"], ok[ok.split == "test"]
med = (tr.annual_heat_kwh / tr.bldgarea).groupby(tr.profile_type).median()
rate = te.profile_type.map(med).fillna((tr.annual_heat_kwh / tr.bldgarea).median())
pd.DataFrame({"property_id": te.property_id, "predicted_heat_kwh": te.bldgarea * rate}).to_csv(
    SUB / "baseline_buildings.csv", index=False)
print("wrote baselines")
