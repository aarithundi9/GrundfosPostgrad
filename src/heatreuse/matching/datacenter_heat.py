"""Engineering estimate of recoverable data center heat (decision D14).

There is no public metered heat data, so this is a transparent scenario model, not a
prediction. Method (docs/plans/pod3_datacenter_heat.md):

    it_load(t)        = capacity * utilization * (1 + a * cos(2*pi*(hour - 15) / 24))
    recoverable(t)    = it_load(t) * capture_fraction        # heat at source_temp_c
    COP               = carnot_eff * T_supply / (T_supply - T_source)   [Kelvin]
    deliverable(t)    = recoverable(t) * COP / (COP - 1)     # heat pump adds its work
    hp_electricity(t) = deliverable(t) / COP

Essentially all IT electricity ends up as heat, so IT load is the heat source. Hourly
energy (kWh) equals average power (kW) over the hour.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from heatreuse import config, timeutils

SCENARIOS = ("low", "mid", "high")
# Used when a site has no public capacity figure. Flagged in the output.
DEFAULT_CAPACITY_MW = {"low": 2.0, "mid": 5.0, "high": 10.0}


def heat_pump_cop(source_temp_c: float, supply_temp_c: float, carnot_eff: float) -> float:
    if supply_temp_c <= source_temp_c:
        return float("inf")  # no lift needed
    t_sup = supply_temp_c + 273.15
    return carnot_eff * t_sup / (supply_temp_c - source_temp_c)


def site_capacity_mw(site: pd.Series, scenario: str) -> tuple[float, bool]:
    """(capacity MW, is_default) for one row of config/datacenters.csv."""
    v = site.get(f"it_capacity_mw_{scenario}")
    if v is None or pd.isna(v):
        return DEFAULT_CAPACITY_MW[scenario], True
    return float(v), False


def hourly_heat(capacity_mw: float, year: int | None = None, **overrides) -> pd.DataFrame:
    """Hourly heat for one site and capacity. Overrides replace settings.datacenter keys."""
    p = {**config.load_settings()["datacenter"], **overrides}
    year = year or config.get("project.weather_year")
    ts = timeutils.canonical_index(year)
    hour_start = (ts - pd.Timedelta(hours=1)).hour.to_numpy()
    shape = 1 + p["diurnal_amplitude"] * np.cos(2 * np.pi * (hour_start - 15) / 24)
    it_kw = capacity_mw * 1000 * p["utilization"] * shape
    recoverable = it_kw * p["capture_fraction"]
    cop = heat_pump_cop(p["source_temp_c"], p["supply_temp_c"], p["carnot_efficiency"])
    if np.isinf(cop):
        deliverable, hp = recoverable, np.zeros_like(recoverable)
    else:
        deliverable = recoverable * cop / (cop - 1)
        hp = deliverable / cop
    return pd.DataFrame({"timestamp": ts, "it_load_kwh": it_kw,
                         "recoverable_heat_kwh": recoverable,
                         "deliverable_heat_kwh": deliverable,
                         "heat_pump_electricity_kwh": hp})


def build_datacenter_heat(dc_ids: list[str] | None = None) -> pd.DataFrame:
    """``datacenter_heat_hourly`` for every site x scenario in config/datacenters.csv."""
    sites = pd.read_csv(config.CONFIG_DIR / "datacenters.csv")
    if dc_ids:
        sites = sites[sites["dc_id"].isin(dc_ids)]
    frames = []
    for _, site in sites.iterrows():
        for sc in SCENARIOS:
            cap, is_default = site_capacity_mw(site, sc)
            df = hourly_heat(cap)
            df.insert(0, "scenario", sc)
            df.insert(0, "dc_id", site["dc_id"])
            df["capacity_mw"] = cap
            df["capacity_is_default"] = is_default
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def annual_summary(heat: pd.DataFrame) -> pd.DataFrame:
    """MWh/yr per site and scenario, for the deck."""
    cols = ["it_load_kwh", "recoverable_heat_kwh", "deliverable_heat_kwh",
            "heat_pump_electricity_kwh"]
    out = heat.groupby(["dc_id", "scenario", "capacity_mw"])[cols].sum() / 1000
    return out.rename(columns=lambda c: c.replace("_kwh", "_mwh")).reset_index()
