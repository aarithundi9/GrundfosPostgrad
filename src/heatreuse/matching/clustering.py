"""OWNER: Pod 3. Spatial clusters of heat demand around a data center -> ``clusters``.

Plan:
  * Points = building centroids in EPSG:2263 (feet; convert eps from metres).
  * DBSCAN(eps=settings.clustering.eps_m, min_samples=...) with
    sample_weight = annual_heat_kwh (dense heat, not just dense buildings).
  * Label -1 = noise (isolated buildings): still candidates in the LP, just not pooled.
  * Report per cluster: n_buildings, annual heat, peak demand, distance to the data
    center, and coincidence() with data center supply.
  * Sensitivity: eps 100/150/250 m.
Why: clusters give the LP natural "branches" and give the map something readable.
"""

from __future__ import annotations

import pandas as pd


def cluster_buildings(buildings: pd.DataFrame, eps_m: float | None = None,
                      min_samples: int | None = None) -> pd.DataFrame:
    """TODO(Pod 3)."""
    raise NotImplementedError
