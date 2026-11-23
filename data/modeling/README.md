# Modeling datasets (ready to use, no downloading or cleaning needed)

```python
import pandas as pd
hourly = pd.read_parquet("data/modeling/hourly_heat.parquet")
train  = pd.read_parquet("data/modeling/building_heat_train.parquet")
predict = pd.read_parquet("data/modeling/building_heat_predict.parquet")
```

Built by `scripts/build_datasets.py` from NREL ComStock/ResStock 2018 (Chelsea, PUMA 3807),
NREL 2018 Manhattan weather, NYC LL84 2024 and PLUTO 26v2. "Heat" everywhere = space
heating + hot water, as useful heat delivered (fuel × boiler efficiency), in kWh.

---

## Track A: `hourly_heat.parquet` (hourly heat demand)

148,920 rows = 17 building types × 8,760 hours of 2018. One row per building type per hour.

| Column | Meaning |
|---|---|
| `timestamp` | hour-ending, Eastern Standard Time (the 01:00 row = 00:00–01:00) |
| `timestamp_local` | same hour on the NYC wall clock (with daylight saving) |
| `profile_type` | building type (`largeoffice`, `multi-family_with_5plus_units`, ...) |
| **`heat_total_kwh`** | **target**: heat used by all buildings of that type in Chelsea that hour |
| `heat_intensity` | `heat_total_kwh / scale_value` (per sq ft for commercial, per apartment for residential). Use this to train one model across types. |
| `space_heating_kwh`, `dhw_kwh` | the two parts of the target (don't use as features) |
| `scale_basis`, `scale_value` | sq ft or apartments represented |
| `models_used`, `low_model_count` | how many simulated buildings make up the profile; types with < 10 are noisy |
| `temp_c`, `rel_humidity_pct`, `wind_speed_ms`, `ghi_wm2` | weather (ghi = sunlight) |
| `hdh_18c` | heating degree-hours: max(0, 18.3 − temp_c) |
| `temp_c_roll24`, `temp_c_lag1`, `temp_c_lag3` | 24 h average temperature, temperature 1 h and 3 h earlier |
| `hour_of_day`, `day_of_week`, `month`, `is_weekend`, `is_holiday` | calendar (from local time) |
| `data_split` | `train` = Jan–Sep, `test` = Oct–Dec |

**Rules**
- Train only on `data_split == "train"`. Don't tune on the test months.
- Features allowed: weather + calendar + `profile_type`. **No past demand** (no lagged
  `heat_total_kwh`): the real buildings we apply this to don't have meter data.
- Submit: CSV with `timestamp, profile_type, predicted_kwh` for every test row (37,536 rows).

## Track B: `building_heat_train.parquet` (annual heat per building)

38,602 NYC buildings that report to LL84 (2024), joined to PLUTO.

| Column group | Columns |
|---|---|
| **Target** | **`annual_heat_kwh`** (also `heat_intensity_kwh_per_sqft` = target / `bldgarea`) |
| Use only these rows | `label_quality_flag == "ok"` (27,838 rows). Others have no heating fuel reported, meter gaps or outlier values |
| Split | `split` = `train` / `test` (fixed 80/20, grouped so multi-building campuses stay together) |
| **Allowed features (PLUTO)** | `bldgarea comarea resarea officearea retailarea garagearea strgearea factryarea otherarea lotarea numbldgs numfloors unitsres unitstotal lotfront lotdepth bldgfront bldgdepth proxcode bsmtcode yearbuilt yearalter1 yearalter2 builtfar building_age years_since_alteration res_share com_share area_per_unit is_condo is_landmark in_historic_district bldgclass bldgclass_letter landuse borough profile_type latitude longitude n_lots zipcode` |
| **Not allowed as features** (LL84-only, so buildings we predict for don't have them) | `largest_property_use_type ll84_profile_type gfa_sqft number_of_buildings *_kbtu site_eui_kbtu_ft heat_from_* gas_only_proxy_kwh on_district_steam estimated_energy` |
| IDs | `property_id bbl address split_group_id parent_property_id` |

How the target is built: gas × (share of gas used for heat + hot water, from NREL, by
building type) × 0.80 + oil × share × 0.80 + steam × share + district hot water, converted to kWh.

Submit: CSV with `property_id, predicted_heat_kwh` for every test row with `label_quality_flag == "ok"`.

## `building_heat_predict.parquet` (where Track B models get used)

8,450 PLUTO lots within 2 km of 111 8th Ave (3,391 within 1 km). Same feature columns as
above, plus `distance_m`, `within_500m`, `within_1000m`, `is_ll84_reporter` and
`reported_heat_kwh` (for lots that report to LL84). The winning model predicts heat for
the rest.

## Scoring

```bash
python scripts/score.py hourly submissions/<yourname>_hourly.csv
python scripts/score.py buildings submissions/<yourname>_buildings.csv
```

Prints your score and adds it to `submissions/leaderboard.csv`. Lower is better.
Hourly is scored on mean CV(RMSE) across building types; buildings on median % error.
Baselines to beat (`scripts/baselines.py`): hourly 0.392, buildings 0.329.
