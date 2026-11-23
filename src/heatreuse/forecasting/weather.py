"""DONE (data loading is now central). NREL AMY2018 weather for Manhattan -> ``weather_hourly`` table.

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


def build_weather_hourly(path=None) -> pd.DataFrame:
    """Steps 1-7 -> ``weather_hourly``."""
    from heatreuse import config, timeutils
    path = path or config.RAW / "nrel" / "weather" / f"{config.get('nrel.weather_county')}_2018.csv"
    df = pd.read_csv(path).drop(columns=DROP, errors="ignore").rename(columns=RENAME)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    timeutils.check_hourly(df)
    df = df.set_index("timestamp")
    bad = (df["temp_c"] < -25) | (df["temp_c"] > 40) | (df["rel_humidity_pct"] < 0) \
        | (df["rel_humidity_pct"] > 100) | (df["ghi_wm2"] < 0)
    df.loc[bad, ["temp_c", "rel_humidity_pct", "ghi_wm2"]] = float("nan")
    gaps = df["temp_c"].isna()
    df = df.interpolate(limit=3, limit_direction="both")
    df["is_interpolated"] = gaps & df["temp_c"].notna()
    if df["temp_c"].isna().any():
        raise ValueError(f"{int(df['temp_c'].isna().sum())} weather hours missing after filling 3 h gaps")
    df["temp_f"] = df["temp_c"] * 9 / 5 + 32
    df["hdh_18c"] = (HDH_BASE_C - df["temp_c"]).clip(lower=0)
    df["temp_c_roll24"] = df["temp_c"].rolling(24, min_periods=1).mean()
    df["temp_c_lag1"] = df["temp_c"].shift(1).bfill()
    df["temp_c_lag3"] = df["temp_c"].shift(3).bfill()
    df = timeutils.add_local_time(df.reset_index())
    return df
