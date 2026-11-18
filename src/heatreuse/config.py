"""Load config/settings.toml and expose standard project paths."""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW = DATA_DIR / "raw"
INTERIM = DATA_DIR / "interim"
# Set HEATREUSE_PROCESSED=data/sample to run everything against synthetic data.
PROCESSED = ROOT / os.environ.get("HEATREUSE_PROCESSED", "data/processed")
OUTPUTS = ROOT / "outputs"


@lru_cache(maxsize=1)
def load_settings() -> dict:
    """Return config/settings.toml as a nested dict (cached)."""
    with open(CONFIG_DIR / "settings.toml", "rb") as f:
        return tomllib.load(f)


def get(path: str):
    """Dotted lookup, e.g. get("study_area.radius_m")."""
    node = load_settings()
    for key in path.split("."):
        node = node[key]
    return node
