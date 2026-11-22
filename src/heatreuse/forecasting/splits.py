"""Train/test split and CV folds (decision D7). Shared by Daksh and Lucent."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd

from heatreuse import config


def assign_split(ts: pd.Series) -> pd.Series:
    """'train' for Jan-Sep, 'test' for Oct-Dec (hour-ending, per settings.split)."""
    s = config.load_settings()["split"]
    ts = pd.to_datetime(ts)
    test = (ts >= pd.Timestamp(s["test_start"])) & (ts <= pd.Timestamp(s["test_end"]))
    return pd.Series(np.where(test, "test", "train"), index=ts.index, name="data_split")


def month_folds(ts: pd.Series, gap_hours: int | None = None
                ) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
    """Leave-one-month-out folds over the TRAIN period only.

    Yields (month, train_idx, val_idx) as positional indices. Rows within ``gap_hours``
    of the held-out month are dropped from training so lag features can't leak.
    Use for tuning; report the mean over folds AND the January/February folds
    (the heating-heavy ones) separately.
    """
    gap = pd.Timedelta(hours=gap_hours if gap_hours is not None
                       else config.get("split.cv_gap_hours"))
    ts = pd.to_datetime(ts).reset_index(drop=True)
    is_train = assign_split(ts).to_numpy() == "train"
    # hour-ending: the hour that ends at 00:00 on the 1st belongs to the previous month
    month = (ts - pd.Timedelta(hours=1)).dt.month
    for m in sorted(month[is_train].unique()):
        val = is_train & (month == m).to_numpy()
        lo, hi = ts[val].min() - gap, ts[val].max() + gap
        trn = is_train & ~val & ~((ts >= lo) & (ts <= hi)).to_numpy()
        yield int(m), np.flatnonzero(trn), np.flatnonzero(val)
