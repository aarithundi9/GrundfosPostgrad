"""OWNER: Pod 2 (Neil/Vedant/Rafa) in weeks 5-6. Interactive map (folium).

Layers (each toggleable):
  1. Data centers: marker sized by deliverable heat (mid scenario), popup with
     low/mid/high MWh/yr and capacity source.
  2. Buildings in the study area: footprint polygons (or circles) colored by
     annual_heat_kwh (sequential palette, log scale), popup: address, type,
     heat_source (reported/predicted), annual MWh.
  3. Clusters: convex hulls per cluster_id.
  4. Recommended matches: connected buildings highlighted + straight lines to the DC;
     popup with served heat and coverage.
  5. Radius rings (500 m / 1 km / 2 km).
Plus a small panel per data center: monthly supply vs demand chart (seasonal_coincidence).
Output: outputs/maps/<dc_id>.html and outputs/maps/citywide.html.
Reads ONLY contract tables (study_area_buildings, clusters, matches, match_summary,
datacenter_heat_hourly), so it can be built against fake data before the models finish.
"""


def build_map(dc_id: str | None = None, out_path=None):
    """TODO(map owners)."""
    raise NotImplementedError
