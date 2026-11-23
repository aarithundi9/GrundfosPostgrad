"""OWNER: Karan. NREL AMY2018 weather for Manhattan -> ``weather_hourly`` table.

Source file (checked on OEDI): comstock_amy2018_release_3/weather/amy2018/G3600610_2018.csv
  8,760 rows, hour-ending EST, first row 2018-01-01 01:00, last row 2019-01-01 00:00.
  So the "last row" open question is answered: the year-end hour is present. Checked
  directly against the downloaded file (Nov 2026): no missing values, all columns
  already inside the documented ranges.
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

Deviation from the step list above, documented here (see docs/decisions.md D16 for the
first-row fill rule): ``build_weather_hourly`` only does steps 1-6 and returns the
DataFrame. Step 7's write happens in the caller (``scripts/run_pipeline.py::step_weather``,
or this module's ``__main__`` block below) -- the same convention Emma's
``forecasting/profiles.py`` uses -- so the table is never written twice.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from heatreuse import config, timeutils

logger = logging.getLogger(__name__)

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

VALUE_COLS = ["temp_c", "rel_humidity_pct", "wind_speed_ms", "ghi_wm2"]
MAX_GAP_HOURS = 3
# (low, high); high=None means no upper bound.
RANGES = {
    "temp_c": (-25.0, 40.0),
    "rel_humidity_pct": (0.0, 100.0),
    "ghi_wm2": (0.0, None),
}
# If more than this share of a column's rows are out of range, something is actually
# wrong with the file and we should stop rather than quietly clip it.
OUT_OF_RANGE_RAISE_FRACTION = 0.01

OUTPUT_COLS = ["timestamp", "timestamp_local", "temp_c", "temp_f", "rel_humidity_pct",
               "wind_speed_ms", "ghi_wm2", "hdh_18c", "temp_c_roll24",
               "temp_c_lag1", "temp_c_lag3", "is_interpolated"]


def _raw_weather_path() -> Path:
    county = config.load_settings()["nrel"]["weather_county"]
    return config.RAW / "nrel" / "weather" / f"{county}_2018.csv"


def _read_raw(path: str | Path | None = None) -> pd.DataFrame:
    """Step 1-2: read the NREL weather CSV, rename, keep the columns we use, add temp_f."""
    df = pd.read_csv(path or _raw_weather_path())
    df = df.rename(columns=RENAME).drop(columns=DROP, errors="ignore")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df[["timestamp"] + VALUE_COLS].sort_values("timestamp").reset_index(drop=True)
    df["temp_f"] = df["temp_c"] * 9 / 5 + 32
    return df


def _check_and_fill_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Step 3 (completeness half) + step 4: full year of hours, short gaps interpolated.

    ``check_hourly`` raises if any hour is missing, duplicated, or extra. Within that
    complete hourly grid, a column can still have missing *values* (e.g. a bad sensor
    reading dropped to NaN upstream); those are linearly interpolated if the gap is
    <= MAX_GAP_HOURS, flagged in ``is_interpolated``. A longer gap raises instead of
    being silently patched -- weather is a primary model input, so a multi-hour hole
    should be visible, not guessed at.
    """
    timeutils.check_hourly(df)
    out = df.sort_values("timestamp").reset_index(drop=True)
    was_missing = out[VALUE_COLS].isna()
    for col in VALUE_COLS:
        out[col] = out[col].interpolate(method="linear", limit=MAX_GAP_HOURS)
    still_missing = out[VALUE_COLS].isna()
    if still_missing.any().any():
        gaps = {c: int(still_missing[c].sum()) for c in VALUE_COLS if still_missing[c].any()}
        raise ValueError(f"weather_hourly: gap(s) longer than {MAX_GAP_HOURS}h in {gaps}; "
                         "not auto-filled, needs a manual look")
    out["is_interpolated"] = was_missing.any(axis=1)
    return out


def _validate_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Step 3 (range half): clip a handful of implausible readings; raise if that's not
    a handful. Decision: clip rather than hard-fail on a few sensor outliers, but raise
    if more than 1% of a column is out of range, since that signals a real data problem
    rather than noise.
    """
    out = df.copy()
    n = len(out)
    for col, (lo, hi) in RANGES.items():
        bad = out[col] < lo
        if hi is not None:
            bad |= out[col] > hi
        n_bad = int(bad.sum())
        if n_bad == 0:
            continue
        frac = n_bad / n
        bound = f"[{lo}, {hi if hi is not None else 'inf'}]"
        if frac > OUT_OF_RANGE_RAISE_FRACTION:
            raise ValueError(f"{col}: {n_bad} of {n} rows ({frac:.1%}) outside {bound}")
        logger.warning("%s: clipping %d of %d rows to %s", col, n_bad, n, bound)
        out[col] = out[col].clip(lower=lo, upper=hi)
    return out


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Step 5: hdh_18c, trailing 24h mean, 1h/3h lags.

    Decision (docs/decisions.md D16): the first hours have no prior history, so rather
    than leave them NaN, ``temp_c_roll24`` uses an expanding mean for the first 23 rows
    (min_periods=1) and ``temp_c_lag1``/``temp_c_lag3`` back-fill their first 1-3 rows
    from hour 1's own reading. This keeps every required contract column populated.
    """
    out = df.sort_values("timestamp").reset_index(drop=True)
    out["hdh_18c"] = (HDH_BASE_C - out["temp_c"]).clip(lower=0)
    out["temp_c_roll24"] = out["temp_c"].rolling(24, min_periods=1).mean()
    out["temp_c_lag1"] = out["temp_c"].shift(1).bfill()
    out["temp_c_lag3"] = out["temp_c"].shift(3).bfill()
    return out


def build_weather_hourly(path: str | Path | None = None) -> pd.DataFrame:
    """Steps 1-6. Returns the ``weather_hourly`` table; the caller writes it (see the
    module docstring's deviation note).
    """
    df = _read_raw(path)
    df = _check_and_fill_gaps(df)
    df = _validate_ranges(df)
    df = _add_features(df)
    df = timeutils.add_local_time(df)
    return df[OUTPUT_COLS]


SUMMER_MONTHS = {6, 7, 8}
WINTER_MONTHS = {12, 1, 2}


def _season_label(month: pd.Series) -> pd.Series:
    out = pd.Series("other", index=month.index)
    out[month.isin(SUMMER_MONTHS)] = "summer"
    out[month.isin(WINTER_MONTHS)] = "winter"
    return out


def alignment_test(profiles: pd.DataFrame, weather: pd.DataFrame,
                   shifts=range(-3, 4), by_type: bool = False) -> pd.DataFrame:
    """Step 8: correlate heat_total_kwh against temp_c shifted by each lag in ``shifts``.

    A positive shift compares heat at hour t to temperature from ``shift`` hours
    earlier (t - shift). The strongest |correlation| (correlation is negative: heat
    rises as temperature falls) should land at shift 0 or +1 -- for the full year and
    for summer and winter separately (plan.md, repo weather.py docstring step 8).

    By default pools ``heat_total_kwh`` across every profile_type/puma into one series
    per timestamp before correlating, which is what the overall/seasonal acceptance
    test above needs. Pass ``by_type=True`` for a per-profile_type breakdown (useful
    for plotting heat vs. temperature by building type).

    Shifts are computed over each series' full chronological timeline BEFORE splitting
    into summer/winter, so a shift of +/-3 never crosses the gap between February and
    December that defining "winter" as {Dec, Jan, Feb} would otherwise create.
    """
    key = ["profile_type"] if by_type else []
    pooled = profiles if by_type else (
        profiles.groupby("timestamp", as_index=False)["heat_total_kwh"].sum())
    merged = pooled.merge(weather[["timestamp", "temp_c", "timestamp_local"]],
                          on="timestamp", how="inner")
    merged = merged.sort_values(key + ["timestamp"] if key else "timestamp").reset_index(drop=True)
    merged["season"] = _season_label(merged["timestamp_local"].dt.month)

    temp_by_group = merged.groupby(key)["temp_c"] if key else merged["temp_c"]
    for shift in shifts:
        merged[f"_shift_{shift}"] = temp_by_group.shift(shift)

    rows = []
    groups = merged.groupby(key[0]) if key else [(None, merged)]
    for group_val, gdf in groups:
        for season in ("all", "summer", "winter"):
            sdf = gdf if season == "all" else gdf[gdf["season"] == season]
            for shift in shifts:
                row = {"season": season, "shift": shift,
                      "r": sdf["heat_total_kwh"].corr(sdf[f"_shift_{shift}"]),
                      "n": len(sdf)}
                if key:
                    row[key[0]] = group_val
                rows.append(row)
    cols = (key + ["season", "shift", "r", "n"]) if key else ["season", "shift", "r", "n"]
    return pd.DataFrame(rows)[cols]


def load_noaa_knyc(path: str | Path, date_col: str = "DATE",
                   temp_col: str = "HourlyDryBulbTemperature") -> pd.DataFrame:
    """Parse a manually-downloaded NOAA NCEI Local Climatological Data CSV for KNYC.

    NOAA reports near :51 past the hour, in LOCAL (DST-aware) clock time, degrees F,
    with occasional trailing quality-flag letters on numeric fields (e.g. "34s").
    This rounds each reading to the nearest clock hour -- treated as the local
    hour-ENDING instant the reading describes -- then converts it to our hour-ending
    EST join key. Since both conventions mark the END of the hour, this is a plain
    timezone conversion (local wall clock -> fixed EST), with none of the +/-1h shift
    that heatreuse.timeutils.add_local_time needs for its hour-START timestamp_local.
    Ambiguous/nonexistent local times from the Nov 4 / Mar 11 DST transitions are
    dropped rather than guessed at.
    """
    raw = pd.read_csv(path, usecols=[date_col, temp_col], low_memory=False)
    temp_f = pd.to_numeric(
        raw[temp_col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    local = pd.to_datetime(raw[date_col]).dt.round("h")
    aware = local.dt.tz_localize(timeutils.LOCAL_TZ, nonexistent="NaT", ambiguous="NaT")
    timestamp = aware.dt.tz_convert(timeutils.EST_FIXED).dt.tz_localize(None)
    out = pd.DataFrame({"timestamp": timestamp, "temp_c": (temp_f - 32) * 5 / 9}).dropna()
    return out.groupby("timestamp", as_index=False)["temp_c"].mean()


def compare_to_noaa(weather: pd.DataFrame, noaa: pd.DataFrame) -> dict:
    """Step 9: compare against NOAA KNYC 2018 (validation only, never a model input).

    ``noaa`` must already be on the hour-ending EST timestamp convention (see
    ``load_noaa_knyc``), with columns ``timestamp``, ``temp_c``. Passes when r >= 0.95
    and monthly means are close (plan.md, docs/timeline.md).
    """
    merged = weather[["timestamp", "temp_c"]].merge(
        noaa[["timestamp", "temp_c"]], on="timestamp", how="inner", suffixes=("_ours", "_noaa"))
    r = merged["temp_c_ours"].corr(merged["temp_c_noaa"])
    monthly = (merged.assign(month=merged["timestamp"].dt.month)
              .groupby("month")[["temp_c_ours", "temp_c_noaa"]].mean())
    max_diff = (monthly["temp_c_ours"] - monthly["temp_c_noaa"]).abs().max()
    return {
        "r": float(r),
        "n": len(merged),
        "monthly_means_ours": monthly["temp_c_ours"].round(2).to_dict(),
        "monthly_means_noaa": monthly["temp_c_noaa"].round(2).to_dict(),
        "max_monthly_diff_c": float(max_diff),
        "passes": bool(r >= 0.95),
    }


if __name__ == "__main__":
    from heatreuse.io import write_table
    write_table(build_weather_hourly(), "weather_hourly")
