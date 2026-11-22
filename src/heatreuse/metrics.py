"""Shared evaluation metrics so every model is scored the same way.

CV(RMSE) and NMBE are the ASHRAE Guideline 14 metrics for building energy models
(hourly calibration targets: CV(RMSE) <= 30%, |NMBE| <= 10%).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mae(y, yhat) -> float:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return float(np.mean(np.abs(y - yhat)))


def rmse(y, yhat) -> float:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def cvrmse(y, yhat) -> float:
    """RMSE / mean(actual). Unitless; compare across building types."""
    m = float(np.mean(y))
    return float("nan") if m == 0 else rmse(y, yhat) / m


def nmbe(y, yhat) -> float:
    """Normalized mean bias error: sum(actual - predicted) / sum(actual). +ve = under-forecast."""
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    s = y.sum()
    return float("nan") if s == 0 else float((y - yhat).sum() / s)


def wape(y, yhat) -> float:
    """Weighted absolute percentage error, robust to the many zero-heat summer hours."""
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    s = np.abs(y).sum()
    return float("nan") if s == 0 else float(np.abs(y - yhat).sum() / s)


def peak_abs_error(y, yhat, top_frac: float = 0.05) -> float:
    """MAE on the hours with the highest actual demand (default top 5%)."""
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    k = max(1, int(len(y) * top_frac))
    idx = np.argsort(y)[-k:]
    return mae(y[idx], yhat[idx])


def score(y, yhat) -> dict:
    return {"mae_kwh": mae(y, yhat), "rmse_kwh": rmse(y, yhat), "cvrmse": cvrmse(y, yhat),
            "nmbe": nmbe(y, yhat), "wape": wape(y, yhat),
            "peak_abs_error_kwh": peak_abs_error(y, yhat)}


def score_frame(pred: pd.DataFrame, by=("model_name", "profile_type", "data_split")) -> pd.DataFrame:
    """Score a forecast_predictions table -> model_scores table."""
    rows = []
    for key, g in pred.groupby(list(by)):
        rows.append({**dict(zip(by, key)), **score(g["actual_kwh"], g["predicted_kwh"])})
    return pd.DataFrame(rows)
