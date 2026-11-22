"""OWNER: Daksh. Baselines every model must beat (scored on Oct-Dec test).

Two baselines, because there are two kinds of model (decision D6):
  * ``same_hour_last_week``: prediction = demand 168 h earlier. Benchmark for Model B
    (short-term forecaster that can see recent demand).
  * ``hour_month_climatology``: mean demand by (profile_type, month, hour_of_day,
    is_weekend) over train. Benchmark for Model A (weather/calendar only).
    NOTE: Oct-Dec months are not in train. Use a degree-hour-scaled version:
    fit demand ~ a(hour, weekend) + b(hour, weekend) * hdh_18c on train.
Output rows go to ``forecast_predictions`` with model_name set to the baseline name;
score with heatreuse.metrics.score_frame.
"""

from __future__ import annotations

import pandas as pd


def same_hour_last_week(features: pd.DataFrame) -> pd.DataFrame:
    """TODO(Daksh)."""
    raise NotImplementedError


def degree_hour_climatology(features: pd.DataFrame) -> pd.DataFrame:
    """TODO(Daksh)."""
    raise NotImplementedError
