"""OWNERS: Rafa (ML model), Vedant (simple model + comparison).

Predict annual heat for buildings that don't report to LL84.

Simple: heat_simple_kwh = bldgarea * median(heat kWh/sqft) of LL84 reporters with the
same profile_type (citywide median fallback for rare types).
ML: LASSO and XGBoost/LightGBM trained on ``ll84_training_table`` citywide.
    Target: log(estimated_annual_heat_kwh / bldgarea), i.e. log heat intensity.
    Predicting intensity, then multiplying by area, handles the heavy size skew.
    Features: PLUTO + footprint columns only (see joins.py).
Evaluation: GroupKFold / 80-20 holdout grouped by split_group_id so multi-building
properties don't leak. Report MAE (kWh), median % error, by size band
(<25k, 25-50k, 50-100k, 100k+ sqft). LL84 has few buildings under 25k sqft, so
expect the simple model to win there; that is a finding, not a failure.
"""

from __future__ import annotations

import pandas as pd

SIZE_BANDS = [0, 25_000, 50_000, 100_000, float("inf")]
SIZE_LABELS = ["<25k", "25-50k", "50-100k", "100k+"]
EXCLUDED_FEATURES_LEAKAGE = ["site_eui", "energy_star_score", "water_use", "electricity_kwh"]


def size_band(area_sqft: pd.Series) -> pd.Series:
    return pd.cut(area_sqft, SIZE_BANDS, labels=SIZE_LABELS, right=False)


def fit_simple(train: pd.DataFrame) -> pd.Series:
    """Median kWh/sqft by profile_type. TODO(Vedant)."""
    raise NotImplementedError


def fit_ml(train: pd.DataFrame, kind: str = "lightgbm"):
    """TODO(Rafa)."""
    raise NotImplementedError


def compare_methods(holdout: pd.DataFrame) -> pd.DataFrame:
    """-> ``method_comparison``. TODO(Vedant)."""
    raise NotImplementedError
