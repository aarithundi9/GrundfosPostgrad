"""BAC × Grundfos Week 3: building-specific heating demand regression.

Run from repository root:
    python notebooks/hourly_demand/daksh_hourly_model.py

Or explicitly:
    python daksh_hourly_model.py --data data/modeling/hourly_heat.parquet \
        --output submissions/daksh_hourly.csv

Approach:
  * Fit a separate multiple linear / Ridge regression for each of 17 building profiles.
  * Weather + calendar features ONLY; never use meter demand from the past.
  * Tune feature set and regularization with blocked validation months (Feb/May/Sep)
    wholly within the Jan--Sep 2018 training partition.
  * Refit on every Jan--Sep row; predict the fixed Oct--Dec test split.
  * CV(RMSE) = RMSE / mean(actual demand), averaged equally over building types.

Requires pandas, numpy, pyarrow and scikit-learn (provided by repository requirements).
"""

from __future__ import annotations
import argparse
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TARGET = "heat_total_kwh"
BASE = ["hdh_18c", "year_sin", "year_cos", "is_weekend", "is_holiday", "hour_sin", "hour_cos", "dow_sin", "dow_cos"]
WEATHER = ["rel_humidity_pct", "wind_speed_ms", "ghi_wm2", "temp_c_roll24", "temp_c_lag1", "temp_c_lag3", "temp_deviation"]
NONLINEAR = ["hdh_squared", "hdh_x_year_sin", "hdh_x_year_cos", "hdh_x_wind", "hdh_x_solar", "hdh_x_weekend", "hdh_x_hour_sin", "hdh_x_hour_cos"]
HOURS = [f"hour_{i}" for i in range(24)]
DOW = [f"dow_{i}" for i in range(7)]
HDH_HOURS = [f"hdh_hour_{i}" for i in range(24)]
WEEKEND_HOURS = [f"weekend_hour_{i}" for i in range(24)]
HDH_WEEKEND_HOURS = [f"hdh_weekend_hour_{i}" for i in range(24)]
HDH_DOW = [f"hdh_dow_{i}" for i in range(7)]
HINGE_KNOTS = [2,4,6,8,10,12,15,18,21,24,28,32]
HINGES = [f"hdh_hinge_{k}" for k in HINGE_KNOTS]
FULL_CORE = ["hdh_18c", "year_sin", "year_cos", "year_sin2", "year_cos2", "is_weekend", "is_holiday"]
HINGE_CORE = ["hdh_18c", "year_sin", "year_cos", "is_weekend", "is_holiday"]

# Seven linear-model variants; none are trees or neural networks.
# Candidate columns and regularization are fixed BEFORE consulting the test set.
CANDIDATES: dict[str,tuple[list[str],float]] = {
 "ols_basic": (BASE, 0),
 "ridge_weather_100": (BASE+WEATHER, 100),
 "ridge_smooth_100": (BASE+WEATHER+NONLINEAR+["hour_sin2","hour_cos2","year_sin2","year_cos2"], 100),
 "ridge_full_100": (FULL_CORE+HOURS+DOW+WEATHER+NONLINEAR+HDH_HOURS+WEEKEND_HOURS+HDH_WEEKEND_HOURS+HDH_DOW, 100),
 "ridge_hinge_100": (HINGE_CORE+HOURS+DOW+WEATHER+HINGES+NONLINEAR+HDH_HOURS, 100),
 "ridge_hinge_full_100": (HINGE_CORE+HOURS+DOW+WEATHER+HINGES+NONLINEAR+HDH_HOURS+WEEKEND_HOURS+HDH_WEEKEND_HOURS, 100),
 "ridge_hinge_full_1000": (HINGE_CORE+HOURS+DOW+WEATHER+HINGES+NONLINEAR+HDH_HOURS+WEEKEND_HOURS+HDH_WEEKEND_HOURS, 1000),
}


def prepare_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Make numeric features from WEATHER and CALENDAR only, with no target leakage."""
    required = ["timestamp","timestamp_local","profile_type","data_split",TARGET,
                "hdh_18c","hour_of_day","day_of_week","month","is_weekend","is_holiday",
                "rel_humidity_pct","wind_speed_ms","ghi_wm2","temp_c","temp_c_roll24",
                "temp_c_lag1","temp_c_lag3"]
    missing = sorted(set(required)-set(raw.columns))
    if missing: raise ValueError(f"Missing required dataset columns: {missing}")
    if raw[["timestamp","profile_type"]].duplicated().any():
        raise ValueError("Duplicate building-type / timestamp keys")
    if set(raw.data_split.unique()) != {"train","test"}:
        raise ValueError("Unexpected data split values")

    d=raw.copy()
    d["timestamp"]=pd.to_datetime(d["timestamp"])
    d["timestamp_local"]=pd.to_datetime(d["timestamp_local"])
    h=d.hour_of_day.astype(int).to_numpy()
    weekday=d.day_of_week.astype(int).to_numpy()
    day=d.timestamp_local.dt.dayofyear.to_numpy()
    hdh=d.hdh_18c.to_numpy(dtype=float)
    weekend=d.is_weekend.to_numpy(dtype=bool)
    f={}
    f["hdh_squared"]=hdh**2
    f["year_sin"]=np.sin(2*np.pi*day/365)
    f["year_cos"]=np.cos(2*np.pi*day/365)
    f["year_sin2"]=np.sin(4*np.pi*day/365)
    f["year_cos2"]=np.cos(4*np.pi*day/365)
    f["hour_sin"]=np.sin(2*np.pi*h/24)
    f["hour_cos"]=np.cos(2*np.pi*h/24)
    f["hour_sin2"]=np.sin(4*np.pi*h/24)
    f["hour_cos2"]=np.cos(4*np.pi*h/24)
    f["dow_sin"]=np.sin(2*np.pi*weekday/7)
    f["dow_cos"]=np.cos(2*np.pi*weekday/7)
    f["hdh_x_year_sin"]=hdh*f["year_sin"]
    f["hdh_x_year_cos"]=hdh*f["year_cos"]
    f["hdh_x_wind"]=hdh*d.wind_speed_ms.to_numpy(dtype=float)
    f["hdh_x_solar"]=hdh*d.ghi_wm2.to_numpy(dtype=float)
    f["hdh_x_weekend"]=hdh*weekend
    f["hdh_x_hour_sin"]=hdh*f["hour_sin"]
    f["hdh_x_hour_cos"]=hdh*f["hour_cos"]
    f["temp_deviation"]=d.temp_c-d.temp_c_roll24
    for hr in range(24):
        f[f"hour_{hr}"]=(h==hr).astype(int)
        f[f"hdh_hour_{hr}"]=hdh*(h==hr)
        f[f"weekend_hour_{hr}"]=((h==hr)&weekend).astype(int)
        f[f"hdh_weekend_hour_{hr}"]=hdh*((h==hr)&weekend)
    for w in range(7):
        f[f"dow_{w}"]=(weekday==w).astype(int)
        f[f"hdh_dow_{w}"]=hdh*(weekday==w)
    for knot in HINGE_KNOTS:
        f[f"hdh_hinge_{knot}"]=np.maximum(0,hdh-knot)
    return pd.concat([d,pd.DataFrame(f,index=d.index)],axis=1)


def new_model(candidate: str):
    """The imputer and scaler are fitted only on the given training rows."""
    _, alpha = CANDIDATES[candidate]
    reg=Ridge(alpha=alpha,solver="lsqr",tol=1e-5,max_iter=2000) if alpha else LinearRegression()
    return make_pipeline(SimpleImputer(strategy="median",keep_empty_features=True), StandardScaler(),reg)


def cvrmse(y, yhat):
    """Exactly the repo score definition for one building profile."""
    y=np.asarray(y,dtype=float)
    yhat=np.asarray(yhat,dtype=float)
    return float(np.sqrt(np.mean((y-yhat)**2))/np.mean(y))


def choose_candidate(training: pd.DataFrame) -> tuple[str,dict[str,float]]:
    """Blocked train-only validation: hold out February, May, September in turn.

    We fit on the OTHER Jan--Sep months, so this is NOT a chronological forecast
    validation. It checks generalization across seasons. No heating-demand lags
    and no test (Oct--Dec) observations enter selection. Pooled RMSE across
    validation months avoids unstable averaging of near-zero summer CV(RMSE).
    """
    scored={}
    for candidate,(cols,_) in CANDIDATES.items():
        residuals=[]
        heldout=[]
        for heldout_month in [2,5,9]:
            fit_rows=training.month!=heldout_month
            val_rows=training.month==heldout_month
            m=new_model(candidate)
            m.fit(training.loc[fit_rows,cols],training.loc[fit_rows,TARGET])
            p=np.maximum(0,m.predict(training.loc[val_rows,cols]))
            y=training.loc[val_rows,TARGET].to_numpy(dtype=float)
            residuals.append(y-p)
            heldout.append(y)
        residuals=np.concatenate(residuals)
        heldout=np.concatenate(heldout)
        scored[candidate]=float(np.sqrt(np.mean(residuals**2))/np.mean(heldout))
    return min(scored,key=scored.get),scored


def fit_all(raw:pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    df=prepare_features(raw)
    predictions=[];results=[]
    for profile in sorted(df.profile_type.unique()):
        one=df[df.profile_type==profile]
        tr=one[one.data_split=="train"]
        te=one[one.data_split=="test"]
        best,validation=choose_candidate(tr)
        cols,_=CANDIDATES[best]
        model=new_model(best)
        model.fit(tr[cols],tr[TARGET])  # final fit uses all Jan--Sep observations
        p=np.maximum(0,model.predict(te[cols]))
        y=te[TARGET].to_numpy(dtype=float)
        predictions.append(pd.DataFrame({"timestamp":te.timestamp.to_numpy(),"profile_type":profile,"predicted_kwh":p}))
        results.append({"profile_type":profile,"selected_model":best,
                        "validation_cvrmse":validation[best],
                        "test_cvrmse":cvrmse(y,p),
                        "test_wape":float(np.sum(np.abs(y-p))/np.sum(y)),
                        "test_nmbe":float(np.sum(y-p)/np.sum(y)),
                        "test_mean_kwh":float(np.mean(y)),
                        "test_hours":len(y),"n_features":len(cols)})
    pred=pd.concat(predictions,ignore_index=True).sort_values(["timestamp","profile_type"]).reset_index(drop=True)
    report=pd.DataFrame(results)
    expected=int((df.data_split=="test").sum())
    assert len(pred)==expected==37536, f"Expected 37,536 predictions, got {len(pred)}"
    assert not pred[["timestamp","profile_type"]].duplicated().any()
    assert pred.predicted_kwh.notna().all() and pred.predicted_kwh.ge(0).all()
    return pred,report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data/modeling/hourly_heat.parquet")
    p.add_argument("--output",default="submissions/daksh_hourly.csv")
    p.add_argument("--report",default="submissions/daksh_hourly_report.csv")
    a=p.parse_args()
    df=pd.read_parquet(a.data)
    pred,report=fit_all(df)
    for path,frame in [(a.output,pred),(a.report,report)]:
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        frame.to_csv(path,index=False)
    print(report[["profile_type","selected_model","test_cvrmse"]].to_string(index=False))
    print(f"Mean CV(RMSE) on test: {report.test_cvrmse.mean():.6f} (baseline 0.392)")
    print(f"Saved {len(pred):,} rows -> {a.output}")
    print(f"Run repository's official scorer: python scripts/score.py hourly {a.output}")

if __name__=="__main__": main()
