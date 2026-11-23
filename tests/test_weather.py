import numpy as np
import pandas as pd
import pytest

from heatreuse import schemas, timeutils
from heatreuse.forecasting import weather


def _clean_weather_df(year: int = 2018) -> pd.DataFrame:
    """A full, gap-free year of synthetic raw weather in the already-renamed shape
    _read_raw would produce (timestamp + VALUE_COLS), so tests don't need a CSV fixture.
    """
    ts = timeutils.canonical_index(year)
    rng = np.random.default_rng(0)
    # a smooth seasonal temperature curve, well inside the documented range
    doy = ts.day_of_year.to_numpy()
    temp_c = 10 - 15 * np.cos(2 * np.pi * doy / 365)
    return pd.DataFrame({
        "timestamp": ts,
        "temp_c": temp_c,
        "rel_humidity_pct": rng.uniform(20, 90, len(ts)),
        "wind_speed_ms": rng.uniform(0, 10, len(ts)),
        "ghi_wm2": rng.uniform(0, 500, len(ts)),
    })


def test_output_is_8760_rows_no_dupes():
    df = _clean_weather_df()
    out = weather._add_features(weather._check_and_fill_gaps(df))
    timeutils.check_hourly(out)  # raises on missing/duplicate/extra hours
    assert len(out) == 8760


def test_dst_dates_present_once():
    df = _clean_weather_df()
    processed = timeutils.add_local_time(weather._add_features(weather._check_and_fill_gaps(df)))
    for day in ["2018-03-11", "2018-11-04"]:
        rows = processed[processed["timestamp"].dt.date == pd.Timestamp(day).date()]
        assert len(rows) == 24
        assert rows["timestamp"].is_unique


def test_short_gap_interpolated_and_flagged():
    df = _clean_weather_df()
    before = df.loc[10, "temp_c"]
    after = df.loc[13, "temp_c"]
    df.loc[11:12, "temp_c"] = np.nan  # a 2-hour gap, <= MAX_GAP_HOURS

    out = weather._check_and_fill_gaps(df)

    assert not out["temp_c"].isna().any()
    expected_11 = before + (after - before) / 3
    expected_12 = before + 2 * (after - before) / 3
    assert out.loc[11, "temp_c"] == pytest.approx(expected_11)
    assert out.loc[12, "temp_c"] == pytest.approx(expected_12)
    assert out["is_interpolated"].tolist() == [i in (11, 12) for i in range(len(out))]


def test_long_gap_raises():
    df = _clean_weather_df()
    df.loc[11:15, "temp_c"] = np.nan  # a 5-hour gap, > MAX_GAP_HOURS

    with pytest.raises(ValueError, match="gap"):
        weather._check_and_fill_gaps(df)


def test_first_row_lag_and_rolling_fill():
    df = _clean_weather_df()
    out = weather._add_features(weather._check_and_fill_gaps(df))

    assert out.loc[0, "temp_c_lag1"] == pytest.approx(out.loc[0, "temp_c"])
    assert out.loc[0:2, "temp_c_lag3"].to_numpy() == pytest.approx(out.loc[0, "temp_c"])
    assert out.loc[0, "temp_c_roll24"] == pytest.approx(out.loc[0, "temp_c"])
    assert out.loc[23, "temp_c_roll24"] == pytest.approx(out.loc[0:23, "temp_c"].mean())
    assert not out[["temp_c_lag1", "temp_c_lag3", "temp_c_roll24"]].isna().any().any()


def test_hdh_18c_and_range_clipping():
    df = _clean_weather_df()
    df.loc[0, "temp_c"] = 25.0   # above base -> hdh 0
    df.loc[1, "temp_c"] = 10.0   # below base -> hdh = 18.3 - 10.0
    df.loc[2, "ghi_wm2"] = -5.0  # physically impossible, should be clipped to 0

    gapped = weather._check_and_fill_gaps(df)
    ranged = weather._validate_ranges(gapped)
    out = weather._add_features(ranged)

    assert out.loc[0, "hdh_18c"] == pytest.approx(0.0)
    assert out.loc[1, "hdh_18c"] == pytest.approx(18.3 - 10.0)
    assert ranged.loc[2, "ghi_wm2"] == pytest.approx(0.0)


def test_range_check_raises_when_most_of_a_column_is_bad():
    df = _clean_weather_df()
    df["temp_c"] = 999.0  # every row implausible -> a real data problem, not noise

    with pytest.raises(ValueError, match="temp_c"):
        weather._validate_ranges(df)


def test_contract_validation():
    out = weather.build_weather_hourly()
    schemas.validate(out, "weather_hourly")  # should not raise

    missing_col = out.drop(columns=["temp_c"])
    with pytest.raises(ValueError, match="missing required"):
        schemas.validate(missing_col, "weather_hourly")


def test_build_weather_hourly_end_to_end():
    path = weather._raw_weather_path()
    if not path.exists():
        pytest.skip(f"{path} not downloaded; run scripts/download_nrel.py first")
    out = weather.build_weather_hourly()
    assert len(out) == 8760
    assert list(out.columns) == weather.OUTPUT_COLS
    schemas.validate(out, "weather_hourly")
