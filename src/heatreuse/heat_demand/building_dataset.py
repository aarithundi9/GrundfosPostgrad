"""Build the building-level modeling tables from LL84 2024 + PLUTO.

Outputs (written by scripts/build_datasets.py to data/modeling/):
  building_heat_train.parquet   one row per LL84 property: PLUTO features + annual heat target
  building_heat_predict.parquet every PLUTO lot within 2 km of 111 8th Ave: same features,
                                plus reported heat where the lot reports to LL84

Target (decisions D1, D2):
  annual_heat_kwh = kWh( gas * f_gas * 0.80 + oil * f_oil * 0.80 + steam * f_dh * 1.0
                         + district hot water * 1.0 )
  f_* = share of that fuel used for space heating + hot water for the building type, from
  NREL ComStock/ResStock (PUMA 3807). Types built from < 10 simulated models fall back to
  EIA national shares (gas 0.69 commercial / 0.68 residential; oil 0.9; steam 1.0).

Features come from PLUTO only, so the model can be applied to buildings that don't report.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from heatreuse import config, crosswalk, units
from heatreuse.heat_demand.joins import norm_bbl

LL84_NUMERIC = ["property_gfa_calculated_1", "property_gfa_self_reported", "natural_gas_use_kbtu",
                "district_steam_use_kbtu", "district_hot_water_use_kbtu", "fuel_oil_1_use_kbtu",
                "fuel_oil_2_use_kbtu", "fuel_oil_4_use_kbtu", "fuel_oil_5_6_use_kbtu",
                "propane_use_kbtu", "electricity_use_grid_purchase_1", "site_eui_kbtu_ft",
                "number_of_buildings", "latitude", "longitude"]
HEAT_FUELS_KBTU = ["natural_gas_use_kbtu", "district_steam_use_kbtu", "district_hot_water_use_kbtu",
                   "fuel_oil_1_use_kbtu", "fuel_oil_2_use_kbtu", "fuel_oil_4_use_kbtu",
                   "fuel_oil_5_6_use_kbtu", "propane_use_kbtu"]
PLUTO_SUM = ["lotarea", "bldgarea", "comarea", "resarea", "officearea", "retailarea", "garagearea",
             "strgearea", "factryarea", "otherarea", "numbldgs", "unitsres", "unitstotal"]
PLUTO_NUMERIC = PLUTO_SUM + ["numfloors", "lotfront", "lotdepth", "bldgfront", "bldgdepth",
                             "proxcode", "bsmtcode", "yearbuilt", "yearalter1", "yearalter2",
                             "builtfar", "latitude", "longitude", "landuse"]
FEATURES = PLUTO_SUM + ["numfloors", "lotfront", "lotdepth", "bldgfront", "bldgdepth", "proxcode",
                        "bsmtcode", "yearbuilt", "yearalter1", "yearalter2", "builtfar",
                        "building_age", "years_since_alteration", "res_share", "com_share",
                        "area_per_unit", "is_condo", "is_landmark", "in_historic_district",
                        "bldgclass", "bldgclass_letter", "landuse", "borough", "profile_type",
                        "latitude", "longitude", "n_lots"]
EIA_FALLBACK = {"natural_gas": {"res": 0.68, "com": 0.69}, "fuel_oil": {"res": 0.9, "com": 0.9},
                "propane": {"res": 0.68, "com": 0.69}, "district_heating": {"res": 1.0, "com": 1.0}}
ANCHOR = (40.7411, -74.0034)  # 111 8th Ave, approx (config/datacenters.csv)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


def load_pluto(path=None) -> pd.DataFrame:
    path = path or config.RAW / "nyc" / "pluto.csv"
    p = pd.read_csv(path, dtype={"bbl": str, "histdist": str, "landmark": str, "condono": str},
                    low_memory=False)
    p["bbl"] = norm_bbl(p["bbl"])
    p = p.dropna(subset=["bbl"]).drop_duplicates("bbl")
    for c in PLUTO_NUMERIC:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p["is_condo"] = p["condono"].notna()
    p["is_landmark"] = p["landmark"].notna()
    p["in_historic_district"] = p["histdist"].notna()
    return p


def lot_features(p: pd.DataFrame) -> pd.DataFrame:
    """Derived per-lot features (same function for train and predict)."""
    f = p.copy()
    f["building_age"] = np.where(f["yearbuilt"] > 0, 2024 - f["yearbuilt"], np.nan)
    last = f[["yearbuilt", "yearalter1", "yearalter2"]].max(axis=1)
    f["years_since_alteration"] = np.where(last > 0, 2024 - last, np.nan)
    area = f["bldgarea"].where(f["bldgarea"] > 0)
    f["res_share"] = (f["resarea"] / area).clip(0, 1)
    f["com_share"] = (f["comarea"] / area).clip(0, 1)
    f["area_per_unit"] = area / f["unitstotal"].where(f["unitstotal"] > 0)
    f["bldgclass_letter"] = f["bldgclass"].astype(str).str[:1]
    f["profile_type"] = [crosswalk.resolve("pluto", c, floor_area_sqft=a, units_res=u,
                                           bldgclass=c, res_share=r)
                         if isinstance(c, str) else "EXCLUDE"
                         for c, a, u, r in zip(f["bldgclass"], f["bldgarea"], f["unitsres"],
                                               f["res_share"])]
    f["n_lots"] = 1
    return f


def _fractions(fuel_fractions: pd.DataFrame) -> dict:
    """{(profile_type, fuel): heat_fraction}, with low-model-count types removed."""
    ff = fuel_fractions.copy()
    return {(r.profile_type, r.fuel): r.heat_fraction for r in ff.itertuples()}


def _frac(fr: dict, low_types: set, ptype: str, fuel: str) -> float:
    kind = "res" if ptype.startswith(("multi", "single", "mobile")) else "com"
    if ptype in low_types or (ptype, fuel) not in fr:
        return EIA_FALLBACK[fuel][kind]
    return fr[(ptype, fuel)]


def clean_ll84(path=None) -> pd.DataFrame:
    path = path or config.RAW / "nyc" / "ll84_2024.csv"
    d = pd.read_csv(path, dtype=str)
    for c in LL84_NUMERIC:
        d[c] = _num(d[c])
    d = d.drop_duplicates("property_id")
    d["bbl_list"] = d["nyc_borough_block_and_lot"].fillna("").str.split(r"[;,]\s*")
    d["gfa_sqft"] = d["property_gfa_calculated_1"].fillna(d["property_gfa_self_reported"])
    return d


def build_target(d: pd.DataFrame, fuel_fractions: pd.DataFrame, low_types: set) -> pd.DataFrame:
    eff = config.load_settings()["heat"]["efficiency"]
    fr = _fractions(fuel_fractions)
    d = d.copy()
    d["ll84_profile_type"] = [crosswalk.resolve("ll84", t, floor_area_sqft=a)
                              if isinstance(t, str) else "mediumoffice"
                              for t, a in zip(d["largest_property_use_type"], d["gfa_sqft"])]
    d.loc[d["ll84_profile_type"] == crosswalk.EXCLUDE, "ll84_profile_type"] = "mediumoffice"
    oil = d[["fuel_oil_1_use_kbtu", "fuel_oil_2_use_kbtu", "fuel_oil_4_use_kbtu",
             "fuel_oil_5_6_use_kbtu"]].sum(axis=1, min_count=1)
    parts = {
        "gas": (d["natural_gas_use_kbtu"], "natural_gas"),
        "oil": (oil, "fuel_oil"),
        "propane": (d["propane_use_kbtu"], "propane"),
        "steam": (d["district_steam_use_kbtu"], "district_heating"),
    }
    heat_kbtu = 0.0
    for name, (kbtu, fuel) in parts.items():
        f = np.array([_frac(fr, low_types, t, fuel) for t in d["ll84_profile_type"]])
        h = kbtu.fillna(0) * f * eff[fuel]
        d[f"heat_from_{name}_kwh"] = units.kbtu_to_kwh(h)
        heat_kbtu = heat_kbtu + h
    hw = d["district_hot_water_use_kbtu"].fillna(0) * eff["district_heating"]
    d["heat_from_district_hot_water_kwh"] = units.kbtu_to_kwh(hw)
    d["annual_heat_kwh"] = units.kbtu_to_kwh(heat_kbtu + hw)
    d["gas_only_proxy_kwh"] = units.kbtu_to_kwh(d["natural_gas_use_kbtu"])

    any_fuel = d[HEAT_FUELS_KBTU].notna().any(axis=1)
    flag = pd.Series("ok", index=d.index)
    flag[d["alert_energy_meter_has_less"] == "Possible Issue"] = "meter_gap"
    flag[~any_fuel | (d["annual_heat_kwh"] <= 0)] = "no_heating_fuel_reported"
    flag[~(d["gfa_sqft"] > 0)] = "invalid_area"
    d["label_quality_flag"] = flag
    d["estimated_energy"] = d["estimated_values_energy"].eq("Yes")
    return d


def _aggregate_lots(rows: pd.DataFrame) -> pd.DataFrame:
    """Many lots per property -> one feature row (sums for sizes, area-weighted rest)."""
    rows = rows.sort_values("bldgarea", ascending=False)
    first = rows.groupby("property_id").first()
    sums = rows.groupby("property_id")[PLUTO_SUM].sum(min_count=1)
    out = first.drop(columns=PLUTO_SUM).join(sums)
    out["numfloors"] = rows.groupby("property_id")["numfloors"].max()
    out["n_lots"] = rows.groupby("property_id").size()
    out = out.reset_index()
    # recompute ratio features on the aggregated sizes
    area = out["bldgarea"].where(out["bldgarea"] > 0)
    out["res_share"] = (out["resarea"] / area).clip(0, 1)
    out["com_share"] = (out["comarea"] / area).clip(0, 1)
    out["area_per_unit"] = area / out["unitstotal"].where(out["unitstotal"] > 0)
    return out


def _split(group_ids: pd.Series, test_frac: float = 0.2) -> pd.Series:
    """Deterministic grouped 80/20 split (same for everyone, every run)."""
    h = group_ids.astype(str).map(lambda s: int(hashlib.md5(s.encode()).hexdigest(), 16) % 100)
    return pd.Series(np.where(h < test_frac * 100, "test", "train"), index=group_ids.index)


def build_train(ll84: pd.DataFrame, lots: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    joined = property_lot_map(ll84).merge(lots, on="bbl", how="inner")
    feats = _aggregate_lots(joined)
    keep = ["property_id", "parent_property_id", "address_1", "largest_property_use_type",
            "ll84_profile_type", "gfa_sqft", "number_of_buildings", "natural_gas_use_kbtu",
            "district_steam_use_kbtu", "district_hot_water_use_kbtu", "site_eui_kbtu_ft",
            "heat_from_gas_kwh", "heat_from_oil_kwh", "heat_from_propane_kwh",
            "heat_from_steam_kwh", "heat_from_district_hot_water_kwh", "gas_only_proxy_kwh",
            "annual_heat_kwh", "label_quality_flag", "estimated_energy"]
    df = feats.merge(ll84[keep], on="property_id", how="inner")
    df["on_district_steam"] = df["district_steam_use_kbtu"].fillna(0) > 0
    df["heat_intensity_kwh_per_sqft"] = df["annual_heat_kwh"] / df["bldgarea"].where(df["bldgarea"] > 0)
    # flag implausible intensities (PLUTO area vs LL84 energy mismatch, campuses, typos)
    ok = df["label_quality_flag"] == "ok"
    lo, hi = df.loc[ok, "heat_intensity_kwh_per_sqft"].quantile([0.01, 0.99])
    bad = ok & ~df["heat_intensity_kwh_per_sqft"].between(lo, hi)
    df.loc[bad, "label_quality_flag"] = "outlier_intensity"
    df.loc[ok & ~(df["bldgarea"] > 0), "label_quality_flag"] = "invalid_area"
    group = df["parent_property_id"].where(~df["parent_property_id"].fillna("Not").str.startswith("Not"),
                                           df["property_id"])
    df["split_group_id"] = group
    df["split"] = _split(group)
    report = {"ll84_properties": len(ll84),
              "matched_to_pluto": int(df["property_id"].nunique()),
              "match_rate": round(df["property_id"].nunique() / len(ll84), 3),
              "usable_ok_rows": int((df["label_quality_flag"] == "ok").sum()),
              "flags": df["label_quality_flag"].value_counts().to_dict()}
    return df, report


def _haversine_m(lat, lon, lat0, lon0):
    lat, lon = np.radians(lat), np.radians(lon)
    lat0, lon0 = np.radians(lat0), np.radians(lon0)
    a = np.sin((lat - lat0) / 2) ** 2 + np.cos(lat) * np.cos(lat0) * np.sin((lon - lon0) / 2) ** 2
    return 6_371_000 * 2 * np.arcsin(np.sqrt(a))


def property_lot_map(ll84: pd.DataFrame) -> pd.DataFrame:
    ex = ll84[["property_id", "bbl_list"]].explode("bbl_list")
    ex["bbl"] = norm_bbl(ex["bbl_list"])
    return ex.dropna(subset=["bbl"]).drop_duplicates(["property_id", "bbl"])[["property_id", "bbl"]]


def build_predict(lots: pd.DataFrame, train: pd.DataFrame, prop_lots: pd.DataFrame,
                  radius_m: float = 2000) -> pd.DataFrame:
    """PLUTO lots near 111 8th Ave (lot-centroid distance; footprint-edge distance comes later).

    Lots belonging to a usable LL84 property get ``reported_heat_kwh`` (property heat split
    across its lots by bldgarea). Everything else is what the models need to predict.
    """
    df = lots.copy()
    df["distance_m"] = _haversine_m(df["latitude"], df["longitude"], *ANCHOR)
    df = df[(df["distance_m"] <= radius_m) & (df["bldgarea"] > 0)
            & (df["profile_type"] != crosswalk.EXCLUDE)].copy()
    for r in (500, 1000):
        df[f"within_{r}m"] = df["distance_m"] <= r
    ok = train.loc[train["label_quality_flag"] == "ok", ["property_id", "annual_heat_kwh"]]
    m = prop_lots.merge(ok, on="property_id").merge(lots[["bbl", "bldgarea"]], on="bbl")
    m["w"] = m["bldgarea"] / m.groupby("property_id")["bldgarea"].transform("sum")
    m["reported_heat_kwh"] = m["annual_heat_kwh"] * m["w"]
    rep = m.groupby("bbl", as_index=False).agg(reported_heat_kwh=("reported_heat_kwh", "sum"),
                                               ll84_property_id=("property_id", "first"))
    df = df.merge(rep, on="bbl", how="left")
    df["is_ll84_reporter"] = df["reported_heat_kwh"].notna()
    return df.sort_values("distance_m").reset_index(drop=True)
