"""OWNER: Vedant. Buildings around a data center -> ``study_area_buildings``.

Steps (Week 2 plan, kept):
  1. Footprints in geopandas, reproject to settings.study_area.crs (EPSG:2263, feet).
  2. Data center polygon from config/datacenters.csv (lat/lon -> containing footprint);
     distance to its EDGE, stored in metres (distance_m, D3).
  3. in_radius for settings.study_area.radius_m; keep sensitivity radii too.
  4. Drop non-buildings (feat_code) and tiny sheds (shape_area < 400 sqft).
  5. Join Neil's building_features; reporters get heat_source="reported"
     (property heat split to BINs), others "predicted".
  6. annual_heat_kwh = reported if available else ML prediction (heat_model_kwh), with
     heat_simple_kwh kept for comparison.
Runs for every dc_id in config/datacenters.csv (citywide expansion = loop).
"""

from __future__ import annotations

import pandas as pd

MIN_FOOTPRINT_SQFT = 400


def datacenter_sites() -> pd.DataFrame:
    from heatreuse import config
    return pd.read_csv(config.CONFIG_DIR / "datacenters.csv")


def select_study_area(footprints, dc_id: str, radius_m: float | None = None):
    """TODO(Vedant)."""
    raise NotImplementedError


def build_study_area_buildings(dc_id: str) -> pd.DataFrame:
    """TODO(Vedant)."""
    raise NotImplementedError
