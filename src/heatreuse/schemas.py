"""Data contract in code. Each handoff table: file, owner, key columns, required columns.

docs/data_contract.md is the readable version; keep the two in sync. ``validate`` is called
by ``heatreuse.io.write_table`` so a table that breaks the contract never lands in
data/processed/.

Naming rules: snake_case; energy columns end in the unit (``_kwh``, ``_kbtu``); hourly
energy is kWh per hour; distances in metres end in ``_m``; areas in square feet end in
``_sqft``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Table:
    name: str
    owner: str
    consumers: str
    keys: list[str]
    required: list[str]
    optional: list[str] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return f"{self.name}.parquet"


TABLES: dict[str, Table] = {t.name: t for t in [
    # ---------------- Pod 1: hourly demand forecasting ----------------
    Table(
        "hourly_profiles", owner="Emma", consumers="Daksh, Lucent, Pod 3",
        keys=["timestamp", "puma", "profile_type"],
        required=["timestamp", "puma", "dataset", "profile_type", "models_used",
                  "scale_basis", "scale_value",
                  "space_heating_fuel_kwh", "dhw_fuel_kwh",
                  "space_heating_kwh", "dhw_kwh", "heat_total_kwh"],
        optional=["natural_gas_heating_kwh", "fuel_oil_heating_kwh", "propane_heating_kwh",
                  "district_heating_kwh", "electricity_heating_kwh",
                  "electricity_heating_supplement_kwh", "fans_heating_kwh",
                  "pumps_heating_kwh", "natural_gas_dhw_kwh", "fuel_oil_dhw_kwh",
                  "propane_dhw_kwh", "district_dhw_kwh", "electricity_dhw_kwh",
                  "low_model_count"],
    ),
    Table(
        "fuel_heat_fractions", owner="Emma", consumers="Rafa",
        keys=["puma", "profile_type", "fuel"],
        required=["puma", "profile_type", "fuel", "fuel_total_kwh",
                  "space_heating_fuel_kwh", "dhw_fuel_kwh", "heat_fraction"],
    ),
    Table(
        "weather_hourly", owner="Karan", consumers="Daksh, Lucent, Rafa (HDD)",
        keys=["timestamp"],
        required=["timestamp", "timestamp_local", "temp_c", "temp_f", "rel_humidity_pct",
                  "wind_speed_ms", "ghi_wm2", "hdh_18c", "temp_c_roll24",
                  "temp_c_lag1", "temp_c_lag3", "is_interpolated"],
    ),
    Table(
        "features_hourly", owner="Daksh", consumers="Lucent",
        keys=["timestamp", "puma", "profile_type"],
        required=["timestamp", "timestamp_local", "puma", "dataset", "profile_type",
                  "heat_total_kwh", "heat_intensity", "temp_c", "rel_humidity_pct",
                  "hdh_18c", "temp_c_roll24", "hour_of_day", "day_of_week", "month",
                  "is_weekend", "is_holiday", "demand_lag_24h", "demand_lag_168h",
                  "data_split"],
    ),
    Table(
        "forecast_predictions", owner="Daksh (baselines), Lucent (models)",
        consumers="model comparison, final deck",
        keys=["timestamp", "profile_type", "model_name"],
        required=["timestamp", "profile_type", "model_name", "data_split",
                  "actual_kwh", "predicted_kwh"],
    ),
    Table(
        "model_scores", owner="Lucent", consumers="final deck",
        keys=["model_name", "profile_type", "data_split"],
        required=["model_name", "profile_type", "data_split", "mae_kwh", "cvrmse",
                  "nmbe", "peak_abs_error_kwh"],
    ),
    Table(
        "hourly_shares", owner="Emma (v1, simulated), Lucent (v2, model)",
        consumers="Pod 3 (matching.hourly_demand)",
        keys=["profile_type", "source", "timestamp"],
        required=["profile_type", "source", "timestamp", "hourly_share"],
    ),
    # ---------------- Pod 2: building heat demand ----------------
    Table(
        "ll84_clean", owner="Rafa", consumers="Neil, Vedant",
        keys=["property_id"],
        required=["property_id", "bbl", "bin", "calendar_year", "property_type",
                  "building_floor_area_sqft", "natural_gas_kbtu", "steam_kbtu",
                  "district_hot_water_kbtu", "fuel_oil_kbtu", "gas_only_proxy_kwh",
                  "estimated_gas_heat_kwh", "estimated_oil_heat_kwh",
                  "estimated_district_heat_kwh", "estimated_annual_heat_kwh",
                  "label_quality_flag"],
        optional=["parent_property_id", "number_of_buildings", "latitude", "longitude",
                  "fuel_oil_1_kbtu", "fuel_oil_2_kbtu", "fuel_oil_4_kbtu",
                  "fuel_oil_5_6_kbtu", "electricity_kwh"],
    ),
    Table(
        "bbl_bin_crosswalk", owner="Neil", consumers="Vedant",
        keys=["property_id", "bbl", "bin"],
        required=["property_id", "bbl", "bin", "base_bbl", "mpluto_bbl", "match_source",
                  "match_status", "n_bbl", "n_bin"],
    ),
    Table(
        "building_features", owner="Neil", consumers="Rafa, Vedant, Pod 3",
        keys=["bin"],
        required=["bin", "bbl", "base_bbl", "bldgarea", "comarea", "resarea", "bldgclass",
                  "landuse", "numfloors", "unitsres", "yearbuilt", "building_age",
                  "footprint_area_sqft", "heightroof", "volume_cuft", "res_share",
                  "com_share", "profile_type", "latitude", "longitude"],
        optional=["property_id", "officearea", "retailarea", "use_group", "numbldgs",
                  "unitstotal", "yearalter1", "yearalter2", "lotarea", "builtfar",
                  "proxcode", "area_per_unit", "on_district_steam"],
    ),
    Table(
        "ll84_training_table", owner="Neil", consumers="Rafa, Vedant",
        keys=["property_id"],
        required=["property_id", "split_group_id", "estimated_annual_heat_kwh",
                  "label_quality_flag", "bldgarea", "profile_type", "n_bbl", "n_bin"],
    ),
    Table(
        "study_area_buildings", owner="Vedant", consumers="Pod 3, map",
        keys=["dc_id", "bin"],
        required=["dc_id", "bin", "bbl", "distance_m", "in_radius", "bldgarea",
                  "profile_type", "res_share", "com_share", "heat_source",
                  "heat_simple_kwh", "heat_model_kwh", "annual_heat_kwh",
                  "latitude", "longitude"],
        optional=["footprint_area_sqft", "heightroof", "on_district_steam", "geometry_wkt"],
    ),
    Table(
        "method_comparison", owner="Vedant", consumers="final deck",
        keys=["method", "size_band"],
        required=["method", "size_band", "mae_kwh", "median_pct_error", "n_buildings"],
    ),
    # ---------------- Pod 3: matching ----------------
    Table(
        "datacenter_heat_hourly", owner="Pod 3", consumers="matching, map",
        keys=["dc_id", "scenario", "timestamp"],
        required=["dc_id", "scenario", "timestamp", "it_load_kwh", "recoverable_heat_kwh",
                  "deliverable_heat_kwh", "heat_pump_electricity_kwh"],
    ),
    Table(
        "building_hourly_demand", owner="Pod 3", consumers="clustering, optimization",
        keys=["dc_id", "bin", "source", "timestamp"],
        required=["dc_id", "bin", "source", "timestamp", "heat_kwh"],
    ),
    Table(
        "clusters", owner="Pod 3", consumers="optimization, map",
        keys=["dc_id", "bin"],
        required=["dc_id", "bin", "cluster_id"],
    ),
    Table(
        "matches", owner="Pod 3", consumers="map, final deck",
        keys=["dc_id", "scenario", "bin"],
        required=["dc_id", "scenario", "bin", "connected", "annual_demand_kwh",
                  "served_heat_kwh", "coverage", "pipe_length_m"],
    ),
    Table(
        "match_summary", owner="Pod 3", consumers="map, final deck",
        keys=["dc_id", "scenario"],
        required=["dc_id", "scenario", "n_connected", "deliverable_heat_kwh",
                  "served_heat_kwh", "supply_utilization", "demand_coverage",
                  "co2_avoided_t"],
    ),
]}


def validate(df: pd.DataFrame, name: str, check_keys: bool = True) -> None:
    """Raise ValueError listing every contract violation for table ``name``."""
    table = TABLES[name]
    problems = []
    missing = [c for c in table.required if c not in df.columns]
    if missing:
        problems.append(f"missing required columns: {missing}")
    if check_keys and not missing:
        dupes = df.duplicated(subset=table.keys).sum()
        if dupes:
            problems.append(f"{dupes} duplicate rows on keys {table.keys}")
    if "timestamp" in df.columns and getattr(df["timestamp"].dtype, "tz", None) is not None:
        problems.append("timestamp must be tz-naive EST hour-ending (see timeutils)")
    if problems:
        raise ValueError(f"[{name}] contract violations (owner {table.owner}):\n  - "
                         + "\n  - ".join(problems))
