import io

import numpy as np
import pandas as pd
import pytest

from heatreuse import timeutils
from heatreuse.forecasting import weather


def _weather_fixture() -> pd.DataFrame:
    ts = timeutils.canonical_index(2018)
    rng = np.random.default_rng(1)
    doy = ts.day_of_year.to_numpy()
    temp_c = 10 - 15 * np.cos(2 * np.pi * doy / 365) + rng.normal(0, 0.2, len(ts))
    df = pd.DataFrame({"timestamp": ts, "temp_c": temp_c,
                      "rel_humidity_pct": 50.0, "wind_speed_ms": 2.0, "ghi_wm2": 100.0})
    df["temp_f"] = df["temp_c"] * 9 / 5 + 32
    df = weather._add_features(weather._check_and_fill_gaps(df))
    return timeutils.add_local_time(df)[weather.OUTPUT_COLS]


def _profiles_fixture(weather_df: pd.DataFrame, true_shift: int = 1) -> pd.DataFrame:
    """heat_total_kwh built as a function of temp_c LAGGED by ``true_shift`` hours plus
    noise, so alignment_test has a known right answer to recover.
    """
    rng = np.random.default_rng(2)
    lagged_temp = weather_df["temp_c"].shift(true_shift).bfill()
    heat = (18.3 - lagged_temp).clip(lower=0) * 50 + rng.normal(0, 5, len(weather_df))
    return pd.DataFrame({
        "timestamp": weather_df["timestamp"],
        "puma": "G36003807",
        "profile_type": "largeoffice",
        "heat_total_kwh": heat.clip(lower=0),
    })


@pytest.mark.parametrize("true_shift", [0, 1])
def test_alignment_recovers_shift_zero_or_one(true_shift):
    weather_df = _weather_fixture()
    profiles = _profiles_fixture(weather_df, true_shift=true_shift)

    result = weather.alignment_test(profiles, weather_df)

    for season in ("all", "summer", "winter"):
        sub = result[result["season"] == season]
        best_shift = sub.loc[sub["r"].abs().idxmax(), "shift"]
        assert best_shift in (0, 1), f"season={season}: best shift was {best_shift}"


def test_alignment_test_by_type_breakdown():
    weather_df = _weather_fixture()
    profiles = pd.concat([
        _profiles_fixture(weather_df, true_shift=1).assign(profile_type="largeoffice"),
        _profiles_fixture(weather_df, true_shift=1).assign(profile_type="multi-family_with_5plus_units"),
    ], ignore_index=True)

    result = weather.alignment_test(profiles, weather_df, by_type=True)

    assert set(result["profile_type"]) == {"largeoffice", "multi-family_with_5plus_units"}
    for _, sub in result[result["season"] == "all"].groupby("profile_type"):
        best_shift = sub.loc[sub["r"].abs().idxmax(), "shift"]
        assert best_shift in (0, 1)


def _noaa_like_fixture(weather_df: pd.DataFrame) -> pd.DataFrame:
    """Re-express our own weather_hourly as a NOAA-shaped raw frame: naive local wall
    clock, ~:51 past the hour, degrees F, with an occasional footnote-letter suffix.

    ``timestamp_local`` is already the naive NY wall-clock hour-START; adding an hour
    gives the naive wall-clock hour-ENDING instant, which is exactly what a NOAA
    DATE string would read (no tz info) for the hour each weather_hourly row covers.
    """
    local_hour_ending = weather_df["timestamp_local"] + pd.Timedelta(hours=1)
    noaa_date = local_hour_ending - pd.Timedelta(minutes=9)  # the :51-past-the-hour quirk
    temp_f = weather_df["temp_f"].round(1).astype(str) + "s"  # footnote-letter suffix
    return pd.DataFrame({"DATE": noaa_date.astype(str), "HourlyDryBulbTemperature": temp_f})


def test_compare_to_noaa_near_perfect_on_self(tmp_path):
    weather_df = _weather_fixture()
    noaa_raw = _noaa_like_fixture(weather_df)
    path = tmp_path / "noaa_knyc_2018.csv"
    noaa_raw.to_csv(path, index=False)

    noaa = weather.load_noaa_knyc(path)
    result = weather.compare_to_noaa(weather_df, noaa)

    assert result["r"] > 0.999
    assert result["max_monthly_diff_c"] < 0.5
    assert result["passes"] is True


def test_noaa_dst_conversion_has_no_dupes():
    weather_df = _weather_fixture()
    around_dst = weather_df[
        weather_df["timestamp"].between("2018-03-10", "2018-03-12")
        | weather_df["timestamp"].between("2018-11-03", "2018-11-05")
    ]
    noaa_raw = _noaa_like_fixture(around_dst)
    noaa = weather.load_noaa_knyc(io.StringIO(noaa_raw.to_csv(index=False)))

    assert noaa["timestamp"].is_unique
    assert not noaa.empty
