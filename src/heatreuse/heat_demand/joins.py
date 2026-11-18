"""OWNER: Neil. LL84 <-> PLUTO <-> footprints crosswalk and building features.

Outputs: ``bbl_bin_crosswalk``, ``building_features`` (one row per BIN, ALL buildings
in scope, reporters or not), ``ll84_training_table`` (one row per property_id), plus a
join report (match rates by route and borough) in outputs/reports/.

Key rules (Week 2 plan, kept): BBL = 10-char zero-padded string (strip PLUTO's ".0");
BIN = 7-char string; "Not Available", blanks and 0 -> missing; known placeholder BINs
(x000000, e.g. 1000000, 2000000, 3000000, 4000000, 5000000) -> missing; explode
semicolon-separated BBL/BIN lists. Match footprints on BIN, then base_bbl;
mpluto_bbl -> PLUTO bbl (handles condos). Spatial fallback (LL84 lat/lon in footprint)
when both fail. Record match_source.

Added (gap fixes):
  * ``profile_type`` on every BIN via heatreuse.crosswalk.resolve (LL84 property type if
    reporter, else PLUTO bldgclass). This is what links Pod 2 to Pod 1's shares.
  * ``on_district_steam``: True if the LL84 row reports steam_kbtu > 0 (D11).
  * Property -> BIN split of heat (needed by Vedant): weight = bldgarea of the BIN's lot
    share, or footprint_area_sqft * numfloors when bldgarea is missing.
  * Keep the feature list to columns available for NON-reporters (PLUTO + footprints).
    No LL84 columns (water use, Energy Star score, EUI...) as model features: the
    buildings we predict for don't have them.
"""

from __future__ import annotations

import pandas as pd

PLACEHOLDER_BINS = {"1000000", "2000000", "3000000", "4000000", "5000000"}


def norm_bbl(s: pd.Series) -> pd.Series:
    """'1007650001.0' / 1007650001 -> '1007650001'; invalid -> <NA>."""
    out = (s.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
           .str.replace(r"[^0-9]", "", regex=True))
    return out.where(out.str.len() == 10).astype("string")


def norm_bin(s: pd.Series) -> pd.Series:
    out = (s.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
           .str.replace(r"[^0-9]", "", regex=True))
    out = out.where((out.str.len() == 7) & ~out.isin(PLACEHOLDER_BINS))
    return out.astype("string")


def build_crosswalk(ll84: pd.DataFrame, pluto: pd.DataFrame,
                    footprints: pd.DataFrame) -> pd.DataFrame:
    """TODO(Neil)."""
    raise NotImplementedError


def build_building_features(pluto: pd.DataFrame, footprints: pd.DataFrame,
                            crosswalk: pd.DataFrame, ll84: pd.DataFrame) -> pd.DataFrame:
    """TODO(Neil)."""
    raise NotImplementedError


def build_training_table(features: pd.DataFrame, crosswalk: pd.DataFrame,
                         ll84: pd.DataFrame) -> pd.DataFrame:
    """TODO(Neil)."""
    raise NotImplementedError
