"""OWNER: Daksh. Join profiles + weather + calendar -> ``features_hourly`` table.

Inputs: ``hourly_profiles`` (Emma), ``weather_hourly`` (Karan).
Join key: ``timestamp`` only (both are EST hour-ending, tz-naive). Never join on
``timestamp_local``.

Steps:
  1. Merge on timestamp; assert row count unchanged (8,760 per profile_type).
  2. Calendar features from timestamp_local: hour_of_day 0-23, day_of_week 0-6,
     month 1-12, is_weekend, is_holiday (``holidays`` package, US federal + NY).
  3. Target heat_total_kwh (D1). Also heat_intensity = heat_total_kwh / scale_value
     (kWh per sqft for ComStock, per dwelling unit for ResStock) so ONE model can learn
     across building types (D6).
  4. demand_lag_24h, demand_lag_168h per profile_type (shift within group!).
     First-week rows: leave NaN; Model B drops them, Model A doesn't use lags.
  5. data_split = forecasting.splits.assign_split(timestamp).
  6. heatreuse.io.write_table(df, "features_hourly").
"""

from __future__ import annotations

import pandas as pd

CALENDAR_FEATURES = ["hour_of_day", "day_of_week", "month", "is_weekend", "is_holiday"]
WEATHER_FEATURES = ["temp_c", "rel_humidity_pct", "wind_speed_ms", "ghi_wm2", "hdh_18c",
                    "temp_c_roll24", "temp_c_lag1", "temp_c_lag3"]
LAG_FEATURES = ["demand_lag_24h", "demand_lag_168h"]


def build_features() -> pd.DataFrame:
    """TODO(Daksh)."""
    raise NotImplementedError
