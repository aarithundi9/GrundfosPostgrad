"""OWNER: Lucent. Gradient boosting (+ LSTM stretch). See docs/plans/pod1_models.md.

Model A, the "profile model" (what the rest of the pipeline uses):
    features = weather + calendar + profile_type (categorical). No demand lags, because
    buildings near the data center have no metered hourly demand to lag.
    target = heat_intensity; predicted kWh = intensity * scale_value.
    One global LightGBM across profile types beats 19 tiny per-type models.
Model B, the "short-term forecaster" (accuracy benchmark only):
    Model A features + demand_lag_24h + demand_lag_168h.
Stretch: LSTM / sequence model on the same split.

Tuning: forecasting.splits.month_folds (leave-one-month-out inside Jan-Sep).
Test: Oct-Dec, once, at the end. Metrics: heatreuse.metrics.score.

Final output for Pod 3: forecasting.shares.shares_from_predictions(...) ->
``hourly_shares`` with source="model_a". (v1 shares from the simulated profiles
already exist, so Pod 3 is never blocked on this.)
"""

from __future__ import annotations

import pandas as pd

MODEL_A_FEATURES = ["temp_c", "rel_humidity_pct", "wind_speed_ms", "ghi_wm2", "hdh_18c",
                    "temp_c_roll24", "temp_c_lag1", "temp_c_lag3", "hour_of_day",
                    "day_of_week", "month", "is_weekend", "is_holiday", "profile_type"]
MODEL_B_FEATURES = MODEL_A_FEATURES + ["demand_lag_24h", "demand_lag_168h"]
TARGET = "heat_intensity"


def train_model_a(features: pd.DataFrame, params: dict | None = None):
    """TODO(Lucent)."""
    raise NotImplementedError


def train_model_b(features: pd.DataFrame, params: dict | None = None):
    """TODO(Lucent)."""
    raise NotImplementedError


def predict(model, features: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Return rows for ``forecast_predictions``. TODO(Lucent)."""
    raise NotImplementedError
