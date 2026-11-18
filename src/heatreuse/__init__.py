"""NYC data center waste heat reuse pipeline (NYU Stern BAC ML x Grundfos).

Package layout (see README.md for owners):
    config, units, timeutils, schemas, io, metrics, crosswalk   shared helpers (PMs)
    forecasting/   Pod 1: hourly heat demand profiles and models
    heat_demand/   Pod 2: annual heat demand per building
    matching/      Pod 3: data center heat, clustering, optimization, economics
    viz/           interactive map
"""

__version__ = "0.1.0"
