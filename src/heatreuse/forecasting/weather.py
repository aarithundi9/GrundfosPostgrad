"""OWNER: Karan. NREL AMY2018 weather for Manhattan -> ``weather_hourly`` table.

Source file (checked on OEDI): comstock_amy2018_release_3/weather/amy2018/G3600610_2018.csv
  8,760 rows, hour-ending EST, first row 2018-01-01 01:00, last row 2019-01-01 00:00.
  So the "last row" open question is answered: the year-end hour is present.
NOAA KNYC 2018 is validation only (step 9), never a model input for 2018.

Steps (Week 2 plan):
  1. Read, rename with RENAME, parse ``timestamp``.
  2. Keep temp, RH, wind speed, GHI. Add temp_f.
  3. heatreuse.timeutils.check_hourly; range checks (-25..40 C, RH 0..100, GHI >= 0).
  4. Interpolate gaps <= 3 h, set is_interpolated; report longer gaps.
  5. Features (agreed split with Daksh: weather-only features live HERE):
     hdh_18c = max(0, 18.3 - temp_c); temp_c_roll24 (trailing 24 h mean);
     temp_c_lag1; temp_c_lag3. Fill the first rows' lags from the same hour
     (or drop them in training; just be consistent and document).
  6. heatreuse.timeutils.add_local_time -> timestamp_local.
  7. heatreuse.io.write_table(df, "weather_hourly").
  8. After Emma's table exists: alignment test (correlate demand with temp shifted
     -3..+3 h; best should be 0 or +1).
  9. NOAA KNYC comparison: r >= 0.95, monthly means close.
"""

from __future__ import annotations

import pandas as pd

RENAME = {
    "date_time": "timestamp",
    "Dry Bulb Temperature [°C]": "temp_c",
    "Relative Humidity [%]": "rel_humidity_pct",
    "Wind Speed [m/s]": "wind_speed_ms",
    "Global Horizontal Radiation [W/m2]": "ghi_wm2",
}
DROP = ["Wind Direction [Deg]", "Direct Normal Radiation [W/m2]",
        "Diffuse Horizontal Radiation [W/m2]"]
HDH_BASE_C = 18.3


def build_weather_hourly() -> pd.DataFrame:
    """Steps 1-7. TODO(Karan)."""
    raise NotImplementedError


def alignment_test(profiles: pd.DataFrame, weather: pd.DataFrame,
                   shifts=range(-3, 4)) -> pd.DataFrame:
    """Step 8: correlation of heat_total_kwh with temp shifted by each lag. TODO(Karan)."""
    raise NotImplementedError


def compare_to_noaa(weather: pd.DataFrame, noaa: pd.DataFrame) -> dict:
    """Step 9. TODO(Karan)."""
    raise NotImplementedError
