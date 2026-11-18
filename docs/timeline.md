# Timeline and per-person tasks (Weeks 3–6)

Weeks 1–2 are done (datasets and pipeline design). From Week 3 every task produces a
**contract table** ([data_contract.md](data_contract.md)) or a function with a test. Each
week ends with a PR merged to `main`. Budget is ~2–3 h per person per week; Week 4
includes Thanksgiving (Thu Nov 26), so it is deliberately light.

**Pod 3 staffing (recommended, PMs to confirm):** Karan joins Pod 3 from Week 4, after the
weather table is merged. A PM (Aarit or Ishaan) co-owns Pod 3 with Karan.

## Week 3 — Nov 17–23: data in, first tables, baselines

**Goal:** every input table exists in `data/processed/`. Baselines scored.

| Who | Task | Output | Done when |
|-----|------|--------|-----------|
| Emma | Implement `forecasting/profiles.py`: download PUMA 3807, build hourly heat (D1, D2), stock totals for ResStock | `hourly_profiles`, `fuel_heat_fractions` | `run_pipeline.py profiles shares` passes; 8,760 rows per type |
| Karan | Implement `forecasting/weather.py` steps 1–7; NOAA check (step 9) | `weather_hourly` | checks pass, NOAA r ≥ 0.95 |
| Daksh | `forecasting/features.py` + both baselines in `baseline.py` | `features_hourly`, baseline rows in `forecast_predictions` | baseline MAE/CV(RMSE) table per type on Oct–Dec |
| Lucent | Set up LightGBM Model A on `features_hourly` (can start on Emma's draft table) with `month_folds` CV | notebook + `models.py` draft | CV scores for Model A |
| Rafa | `heat_demand/ll84.py`: clean 2024 LL84, composite target | `ll84_clean` | count of usable rows by quality flag |
| Neil | `heat_demand/joins.py`: keys, crosswalk, join report | `bbl_bin_crosswalk`, join report | match rates by route/borough |
| Vedant | Study-area selection for 111 8th Ave (radius rings), `fit_simple` | draft `study_area_buildings` (no ML yet) | building count in 500 m / 1 km / 2 km |
| PMs | Confirm decisions D1–D15, assign Pod 3, email Grundfos (questions in [gaps.md](gaps.md) §E) | updated `decisions.md` | — |

## Week 4 — Nov 24–30: models v1 (Thanksgiving week, light)

**Goal:** first real model beats its baseline; heat estimates for every study-area building.

| Who | Task | Output |
|-----|------|--------|
| Lucent | Model A + Model B tuned; score on test **once** | `forecast_predictions`, `model_scores` |
| Daksh | Error analysis: by type, month, peak hours; holiday/DST check | plots in `outputs/figures/` |
| Emma | Sensitivity PUMAs 3808/3810: how different are the shapes? | short note + plot |
| Rafa | ML model (LASSO + LightGBM) on `ll84_training_table` | `fit_ml`, holdout scores |
| Neil | `building_features` + `ll84_training_table` with `profile_type` for every BIN | both tables |
| Vedant | Simple vs ML comparison by size band | `method_comparison` |
| Karan + PM (Pod 3) | Review the data center heat scenarios with Grundfos input; `clustering.py` DBSCAN on synthetic data (`make_sample_data.py`) | `clusters` on sample data |

## Week 5 — Dec 1–7: put it together for 111 8th Ave

**Goal:** a full answer for one data center: which buildings, and how well demand matches supply by hour and season.

| Who | Task | Output |
|-----|------|--------|
| Lucent | Model shares v2 (`shares_from_predictions`); LSTM stretch only if Model A is done | `hourly_shares` (source `model_a`) |
| Daksh + Emma | Compare v1 vs v2 shares; feed `seasonal_coincidence` charts | figures |
| Vedant | Final `study_area_buildings` with `annual_heat_kwh` | table |
| Pod 3 | `building_hourly_demand` → clusters → `greedy_baseline` → `solve_matching` (MILP, representative days) | `matches`, `match_summary` for 111 8th Ave × 3 scenarios |
| Rafa + Neil | Map v1 from contract tables (`viz/map.py`) | `outputs/maps/dc_111_8th_ave.html` |
| PMs | Deck outline; check-in with Grundfos on early results | outline |

## Week 6 — Dec 8–14: citywide run, economics, presentation

**Goal:** final presentation and a clean repo.

| Who | Task | Output |
|-----|------|--------|
| Vedant + Pod 3 | Loop the pipeline over the other data centers in `config/datacenters.csv` (cut first if behind) | `match_summary` for all sites |
| Pod 3 | Carbon (`co2_avoided_t`) for each scenario; costs only if inputs are sourced | numbers for the deck |
| Rafa + Neil | Map v2: citywide layer, popups, radius rings | `outputs/maps/citywide.html` |
| Pod 1 | Final model comparison table: baselines vs GBM (vs LSTM) | `model_scores` + one slide |
| Everyone | README per module up to date, notebooks cleaned, tests pass | merged `main` |
| PMs | Final presentation to Grundfos | deck |

## What gets cut first if behind (from the scope's risk section)
1. LSTM (stretch).
2. Citywide expansion: present 111 8th Ave only, plus a "how to run it for others" slide.
3. Costs: present carbon only, with costs as next steps.
