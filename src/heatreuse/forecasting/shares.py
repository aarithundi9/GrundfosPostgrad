"""Hourly shares: each profile type's 8,760 hourly fractions of its annual heat.

Pod 3 multiplies a building's ANNUAL heat (Pod 2) by these shares to get its hourly
demand. Shares are plain normalization (value / annual sum), NOT softmax: softmax
would exponentiate kWh values and distort the shape.

v1 (source="simulated_2018"): straight from the NREL profiles. Available as soon as
Emma's table exists, so Pod 3 is never blocked on modeling.
v2 (source="model_a"): from Lucent's Model A predictions; lets the pipeline run on other
weather years and smooths sparse profile types.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from heatreuse import config


def normalize(values) -> np.ndarray:
    v = np.clip(np.asarray(values, float), 0, None)
    total = v.sum()
    if total <= 0:
        raise ValueError("annual total is zero; cannot form shares")
    return v / total


def shares_from_profiles(hourly_profiles: pd.DataFrame, puma: str | None = None,
                         value_col: str = "heat_total_kwh",
                         source: str = "simulated_2018") -> pd.DataFrame:
    """hourly_profiles -> hourly_shares for one PUMA (default: primary PUMA)."""
    puma = puma or config.get("nrel.primary_puma")
    df = hourly_profiles[hourly_profiles["puma"] == puma]
    if df.empty:
        raise ValueError(f"no rows for puma {puma}")
    out = df[["profile_type", "timestamp"]].copy()
    out["hourly_share"] = df.groupby("profile_type")[value_col].transform(
        lambda s: pd.Series(normalize(s), index=s.index))
    out["source"] = source
    return out[["profile_type", "source", "timestamp", "hourly_share"]].reset_index(drop=True)


def shares_from_predictions(pred: pd.DataFrame, model_name: str = "model_a") -> pd.DataFrame:
    """forecast_predictions (full year, one model) -> hourly_shares."""
    df = pred[pred["model_name"] == model_name]
    out = df[["profile_type", "timestamp"]].copy()
    out["hourly_share"] = df.groupby("profile_type")["predicted_kwh"].transform(
        lambda s: pd.Series(normalize(s), index=s.index))
    out["source"] = model_name
    return out[["profile_type", "source", "timestamp", "hourly_share"]].reset_index(drop=True)


def check_shares(shares: pd.DataFrame, tol: float = 1e-9) -> None:
    sums = shares.groupby(["profile_type", "source"])["hourly_share"].sum()
    bad = sums[(sums - 1).abs() > tol]
    if len(bad):
        raise ValueError(f"shares do not sum to 1: {bad.to_dict()}")
    if (shares["hourly_share"] < 0).any():
        raise ValueError("negative shares")
