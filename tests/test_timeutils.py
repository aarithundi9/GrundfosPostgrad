import pandas as pd
import pytest

from heatreuse import timeutils


def test_canonical_index_2018():
    idx = timeutils.canonical_index(2018)
    assert len(idx) == 8760
    assert idx[0] == pd.Timestamp("2018-01-01 01:00")
    assert idx[-1] == pd.Timestamp("2019-01-01 00:00")


def test_to_hourly_is_hour_ending():
    ts = pd.date_range("2018-01-01 00:15", "2018-01-01 02:00", freq="15min")
    df = pd.DataFrame({"timestamp": ts, "v": range(1, len(ts) + 1)})
    out = timeutils.to_hourly(df, ["v"])
    assert list(out["timestamp"]) == [pd.Timestamp("2018-01-01 01:00"), pd.Timestamp("2018-01-01 02:00")]
    assert list(out["v"]) == [1 + 2 + 3 + 4, 5 + 6 + 7 + 8]


def test_full_year_15min_gives_8760():
    ts = pd.date_range("2018-01-01 00:15", "2019-01-01 00:00", freq="15min")
    assert len(ts) == 35040
    out = timeutils.to_hourly(pd.DataFrame({"timestamp": ts, "v": 1.0}), ["v"])
    timeutils.check_hourly(out)
    assert (out["v"] == 4).all()


def test_local_time_handles_dst_without_changing_rows():
    df = pd.DataFrame({"timestamp": timeutils.canonical_index(2018)})
    out = timeutils.add_local_time(df)
    assert len(out) == 8760 and out["timestamp"].is_unique
    # Jan: first hour-ending row 01:00 EST -> wall-clock hour 0
    assert out["timestamp_local"].iloc[0] == pd.Timestamp("2018-01-01 00:00")
    # July: EST 12:00 hour-ending = 11:00-12:00 EST = 12:00-13:00 EDT
    row = out[out["timestamp"] == pd.Timestamp("2018-07-01 12:00")]
    assert row["timestamp_local"].iloc[0] == pd.Timestamp("2018-07-01 12:00")


def test_check_hourly_catches_missing_hour():
    df = pd.DataFrame({"timestamp": timeutils.canonical_index(2018)[1:]})
    with pytest.raises(ValueError, match="missing"):
        timeutils.check_hourly(df)


def test_tz_aware_rejected():
    df = pd.DataFrame({"timestamp": pd.date_range("2018-01-01", periods=4, freq="15min", tz="UTC"), "v": 1})
    with pytest.raises(ValueError):
        timeutils.to_hourly(df, ["v"])
