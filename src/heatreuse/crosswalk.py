"""Map LL84 property types and PLUTO building classes to NREL profile types (decision D5).

The table is config/building_type_crosswalk.csv. Values starting with ``@`` are families
resolved here using size, units or floor-area shares.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from heatreuse import config

EXCLUDE = "EXCLUDE"


@lru_cache(maxsize=1)
def load_crosswalk() -> pd.DataFrame:
    return pd.read_csv(config.CONFIG_DIR / "building_type_crosswalk.csv")


def valid_profile_types() -> set[str]:
    s = config.load_settings()["nrel"]
    return set(s["comstock_types"]) | set(s["resstock_types"])


def _resolve_family(token: str, floor_area_sqft: float | None, units_res: float | None,
                    bldgclass: str | None, res_share: float | None) -> str:
    a = floor_area_sqft or 0
    if token == "@office":
        return "smalloffice" if a < 25_000 else "mediumoffice" if a < 150_000 else "largeoffice"
    if token == "@hotel":
        return "smallhotel" if a < 75_000 else "largehotel"
    if token == "@school":
        return "primaryschool" if a < 100_000 else "secondaryschool"
    if token == "@health":
        return "hospital" if (bldgclass or "").upper().startswith("I1") else "outpatient"
    if token == "@multifamily":
        u = units_res or 0
        if u >= 5 or u == 0:   # unknown units: Manhattan default is 5+
            return "multi-family_with_5plus_units"
        return "multi-family_with_2_-_4_units" if u >= 2 else "single-family_attached"
    if token == "@condo":
        cls = (bldgclass or "").upper()
        return _resolve_family("@office", a, units_res, cls, res_share) if cls.startswith("R5") \
            else "multi-family_with_5plus_units"
    if token == "@mixed":
        # Dominant use. For a blended profile use mix_weights() instead.
        if res_share is not None and res_share >= 0.5:
            return _resolve_family("@multifamily", a, units_res, bldgclass, res_share)
        return _resolve_family("@office", a, units_res, bldgclass, res_share)
    raise KeyError(token)


def resolve(source: str, value: str, floor_area_sqft=None, units_res=None,
            bldgclass=None, res_share=None) -> str:
    """Return a concrete profile_type (or "EXCLUDE") for an LL84/PLUTO value.

    source="ll84": value is the LL84 "Largest Property Use Type".
    source="pluto": value is the PLUTO bldgclass (first letter is used).
    """
    cw = load_crosswalk()
    if source == "pluto":
        bldgclass = bldgclass or value
        value = str(value)[:1].upper()
    row = cw[(cw["source"] == source) & (cw["source_value"] == value)]
    if row.empty:
        if source == "ll84" and bldgclass:
            return resolve("pluto", bldgclass, floor_area_sqft, units_res, bldgclass, res_share)
        return "mediumoffice"  # documented fallback; count how often this happens
    token = row["profile_type"].iloc[0]
    if token in ("@pluto", "@pluto_misc"):
        if source == "ll84" and bldgclass:
            return resolve("pluto", bldgclass, floor_area_sqft, units_res, bldgclass, res_share)
        return "mediumoffice"
    if token.startswith("@"):
        return _resolve_family(token, floor_area_sqft, units_res, bldgclass, res_share)
    return token


def mix_weights(res_share: float, com_profile: str, res_profile: str =
                "multi-family_with_5plus_units") -> dict[str, float]:
    """Blend weights for mixed-use buildings: {profile_type: share of annual heat}."""
    res_share = float(min(max(res_share, 0.0), 1.0))
    w = {res_profile: res_share, com_profile: 1.0 - res_share}
    return {k: v for k, v in w.items() if v > 0}
