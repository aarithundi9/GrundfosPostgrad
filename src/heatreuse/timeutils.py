"""One time convention for the whole project (decision D4).

* Join key column is ``timestamp``: tz-naive, Eastern Standard Time (UTC-5) all year,
  HOUR-ENDING. The 01:00 row covers 00:00-01:00.
* 2018 has exactly 8,760 rows: 2018-01-01 01:00 ... 2019-01-01 00:00.
* NREL ComStock/ResStock 15-minute rows and the NREL weather file already use this
  convention, so never localize the join key to America/New_York (that inserts a gap on
  2018-03-11 and a duplicate on 2018-11-04 and shifts every summer hour).
* ``timestamp_local`` (America/New_York wall clock) exists only to build calendar features
  such as hour_of_day, because building schedules follow daylight saving.
"""

from __future__ import annotations

import pandas as pd

EST_FIXED = "Etc/GMT+5"  # UTC-5 all year (the sign in the name is reversed on purpose)
LOCAL_TZ = "America/New_York"


def canonical_index(year: int = 2018) -> pd.DatetimeIndex:
    """The 8,760 (or 8,784) hour-ending EST timestamps for a year."""
    start = pd.Timestamp(year=year, month=1, day=1, hour=1)
    end = pd.Timestamp(year=year + 1, month=1, day=1, hour=0)
    return pd.date_range(start, end, freq="h", name="timestamp")


def to_hourly(df: pd.DataFrame, value_cols: list[str], ts_col: str = "timestamp",
              group_cols: list[str] | None = None) -> pd.DataFrame:
    """Sum 15-minute (period-ending) rows to hour-ending hourly rows.

    The 01:00 output row is the sum of the 00:15, 00:30, 00:45 and 01:00 input rows.
    """
    group_cols = group_cols or []
    out = df.copy()
    out[ts_col] = pd.to_datetime(out[ts_col])
    if out[ts_col].dt.tz is not None:
        raise ValueError("timestamp must be tz-naive EST (see heatreuse.timeutils)")
    # ceil to the hour: 00:15..01:00 -> 01:00 (period-ending)
    out["_hour"] = out[ts_col].dt.ceil("h")
    agg = out.groupby(group_cols + ["_hour"], as_index=False)[value_cols].sum()
    return agg.rename(columns={"_hour": "timestamp"})


def add_local_time(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    """Add ``timestamp_local`` (naive wall-clock New York time) for calendar features.

    Uses the hour START (timestamp - 1h) so the 01:00 hour-ending row maps to the
    00:00-01:00 wall-clock hour, i.e. hour_of_day 0.
    """
    out = df.copy()
    start = (pd.to_datetime(out[ts_col]) - pd.Timedelta(hours=1)).dt.tz_localize(EST_FIXED)
    out["timestamp_local"] = start.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    return out


def check_hourly(df: pd.DataFrame, year: int = 2018, ts_col: str = "timestamp",
                 by: list[str] | None = None) -> None:
    """Raise if any group is missing hours, has duplicates or extra rows."""
    expected = canonical_index(year)
    groups = df.groupby(by) if by else [(None, df)]
    for key, g in groups:
        ts = pd.DatetimeIndex(pd.to_datetime(g[ts_col]))
        if ts.has_duplicates:
            raise ValueError(f"{key}: duplicate timestamps")
        missing = expected.difference(ts)
        extra = ts.difference(expected)
        if len(missing) or len(extra):
            raise ValueError(f"{key}: {len(missing)} missing hours (first {list(missing[:3])}), "
                             f"{len(extra)} unexpected (first {list(extra[:3])})")
