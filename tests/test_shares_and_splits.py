import numpy as np
import pandas as pd
import pytest

from heatreuse import timeutils
from heatreuse.forecasting import shares, splits


def _profiles():
    ts = timeutils.canonical_index(2018)
    rng = np.random.default_rng(0)
    return pd.concat([pd.DataFrame({"timestamp": ts, "puma": "G36003807", "profile_type": p,
                                    "heat_total_kwh": rng.uniform(0, 100, len(ts))})
                      for p in ["largeoffice", "multi-family_with_5plus_units"]])


def test_shares_sum_to_one():
    s = shares.shares_from_profiles(_profiles())
    shares.check_shares(s)
    assert len(s) == 2 * 8760


def test_shares_are_not_softmax():
    s = shares.normalize([1, 1, 2])
    assert np.allclose(s, [0.25, 0.25, 0.5])


def test_zero_total_raises():
    with pytest.raises(ValueError):
        shares.normalize([0, 0])


def test_split_boundaries():
    ts = pd.Series(timeutils.canonical_index(2018))
    sp = splits.assign_split(ts)
    assert sp[ts == pd.Timestamp("2018-10-01 00:00")].item() == "train"   # last Sep hour
    assert sp[ts == pd.Timestamp("2018-10-01 01:00")].item() == "test"
    assert (sp == "test").sum() == (31 + 30 + 31) * 24


def test_month_folds_no_overlap_and_gap():
    ts = pd.Series(timeutils.canonical_index(2018))
    folds = list(splits.month_folds(ts, gap_hours=168))
    assert [m for m, _, _ in folds] == list(range(1, 10))
    for m, tr, va in folds:
        assert not set(tr) & set(va)
        gap = (ts[tr].to_numpy()[:, None] - ts[va].to_numpy()[None, :])
        assert np.abs(gap).min() > pd.Timedelta(hours=168)
