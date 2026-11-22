"""How well demand lines up with supply over time (answers the project's core question)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def coincidence(supply_kwh, demand_kwh) -> dict:
    """served = min(supply, demand) each hour.

    demand_coverage    = served / total demand   (share of buildings' heat we can cover)
    supply_utilization = served / total supply   (share of data center heat put to use)
    hours_supply_short = hours where demand > supply
    """
    s, d = np.asarray(supply_kwh, float), np.asarray(demand_kwh, float)
    served = np.minimum(s, d)
    return {"served_heat_kwh": float(served.sum()),
            "demand_coverage": float(served.sum() / d.sum()) if d.sum() else float("nan"),
            "supply_utilization": float(served.sum() / s.sum()) if s.sum() else float("nan"),
            "hours_supply_short": int((d > s).sum())}


def seasonal_coincidence(ts, supply_kwh, demand_kwh) -> pd.DataFrame:
    """coincidence() per month, for the 'across seasons' part of the question."""
    df = pd.DataFrame({"timestamp": pd.to_datetime(ts), "s": supply_kwh, "d": demand_kwh})
    df["month"] = (df["timestamp"] - pd.Timedelta(hours=1)).dt.month
    return pd.DataFrame([{"month": m, **coincidence(g["s"], g["d"])}
                         for m, g in df.groupby("month")])


def representative_days(ts, values: np.ndarray) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Collapse 8,760 h to 12 months x {weekday, weekend} x 24 h = 576 periods.

    values: (n_series x n_hours). Returns (period index frame, mean values
    (n_series x 576), weights = number of real hours each period stands for).
    """
    t = pd.to_datetime(pd.Series(ts)) - pd.Timedelta(hours=1)  # hour start
    key = pd.DataFrame({"month": t.dt.month, "weekend": t.dt.dayofweek >= 5, "hour": t.dt.hour})
    groups = key.groupby(["month", "weekend", "hour"]).indices
    periods = pd.DataFrame(list(groups.keys()), columns=["month", "weekend", "hour"])
    vals = np.atleast_2d(values)
    means = np.stack([vals[:, idx].mean(axis=1) for idx in groups.values()], axis=1)
    weights = np.array([len(idx) for idx in groups.values()], float)
    return periods, means, weights
