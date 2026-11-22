"""Annual heat per building (Pod 2) x hourly shares (Pod 1) -> hourly demand per building.

    heat_kwh[bin, t] = annual_heat_kwh[bin] * sum_p weight[bin, p] * share[p, t]

weight: 1.0 on the building's profile_type, except mixed-use commercial buildings with
0.1 < res_share < 0.9, which blend res_share of the multifamily 5+ profile with the
rest on their commercial profile.

Size: ~2,000 buildings in 1 km of 111 8th Ave x 8,760 h = ~17.5M rows. Filter to
``in_radius`` and a minimum annual heat before calling, or use ``demand_matrix``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RES_PROFILE = "multi-family_with_5plus_units"
RES_TYPES = {"multi-family_with_5plus_units", "multi-family_with_2_-_4_units",
             "single-family_attached", "single-family_detached", "mobile_home"}


def profile_weights(buildings: pd.DataFrame) -> pd.DataFrame:
    """Long table (bin, profile_type, weight); weights sum to 1 per bin."""
    rows = []
    for b in buildings.itertuples(index=False):
        rs = getattr(b, "res_share", np.nan)
        if b.profile_type not in RES_TYPES and pd.notna(rs) and 0.1 < rs < 0.9:
            rows += [(b.bin, RES_PROFILE, rs), (b.bin, b.profile_type, 1 - rs)]
        else:
            rows.append((b.bin, b.profile_type, 1.0))
    return pd.DataFrame(rows, columns=["bin", "profile_type", "weight"])


def demand_matrix(buildings: pd.DataFrame, shares: pd.DataFrame, source: str = "simulated_2018"
                  ) -> tuple[np.ndarray, list, pd.DatetimeIndex]:
    """Dense (n_buildings x n_hours) kWh matrix. Faster/smaller than the long table."""
    sh = shares[shares["source"] == source].pivot(index="profile_type", columns="timestamp",
                                                   values="hourly_share")
    w = profile_weights(buildings).pivot_table(index="bin", columns="profile_type",
                                               values="weight", aggfunc="sum", fill_value=0)
    missing = set(w.columns) - set(sh.index)
    if missing:
        raise KeyError(f"no shares for profile types {missing} (source={source})")
    w = w.reindex(buildings["bin"])
    annual = buildings.set_index("bin")["annual_heat_kwh"].reindex(w.index).to_numpy()
    m = (w.to_numpy() @ sh.loc[w.columns].to_numpy()) * annual[:, None]
    return m, list(w.index), pd.DatetimeIndex(sh.columns)


def build_building_hourly_demand(buildings: pd.DataFrame, shares: pd.DataFrame, dc_id: str,
                                 source: str = "simulated_2018") -> pd.DataFrame:
    """Long ``building_hourly_demand`` table for one data center."""
    m, bins, ts = demand_matrix(buildings, shares, source)
    out = pd.DataFrame({"bin": np.repeat(bins, len(ts)),
                        "timestamp": np.tile(ts, len(bins)),
                        "heat_kwh": m.ravel()})
    out.insert(0, "dc_id", dc_id)
    out.insert(2, "source", source)
    return out
