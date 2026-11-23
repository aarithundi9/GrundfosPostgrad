# NYC Data Center Waste Heat Reuse

NYU Stern BAC Machine Learning team × Grundfos (Fall 2026, Nov 3 – Dec 14).
PMs: Aarit Hundi, Ishaan Sharma.

**Question:** for a given NYC data center, which nearby buildings are the best users of
its waste heat, and how well does their heat demand line up with the heat the data
center produces over the day and across seasons?

Deep-dive: **111 8th Avenue**, then the same pipeline on other Manhattan data centers.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.11+
pip install -r requirements.txt
pytest -q                                              # should pass
python scripts/download_nrel.py                        # NREL profiles + weather (~150 MB)
python scripts/download_nyc.py                         # LL84, PLUTO, footprints (large)
python scripts/run_pipeline.py --list                  # see the steps
python scripts/run_pipeline.py datacenter_heat         # already works
python scripts/make_sample_data.py                     # synthetic tables for Pod 3 / map work
```

## Pipeline and owners

| Step | Module | Owner | Output table | Status |
|---|---|---|---|---|
| Hourly building profiles | `forecasting/profiles.py` | Emma | `hourly_profiles`, `fuel_heat_fractions` | stub, columns verified |
| Weather | `forecasting/weather.py` | Karan | `weather_hourly` | stub, columns verified |
| Hourly shares v1 | `forecasting/shares.py` | Emma | `hourly_shares` | **done** |
| Features + baselines | `forecasting/features.py`, `baseline.py` | Daksh | `features_hourly`, `forecast_predictions` | stub |
| GBM / LSTM | `forecasting/models.py` | Lucent | `forecast_predictions`, `model_scores`, shares v2 | stub |
| CV splits | `forecasting/splits.py` | shared | — | **done** |
| LL84 cleaning + target | `heat_demand/ll84.py` | Rafa | `ll84_clean` | stub |
| Joins + features | `heat_demand/joins.py` | Neil | `bbl_bin_crosswalk`, `building_features`, `ll84_training_table` | key helpers done |
| Study area + prediction | `heat_demand/study_area.py`, `model.py` | Vedant, Rafa | `study_area_buildings`, `method_comparison` | stub |
| Data center heat | `matching/datacenter_heat.py` | Pod 3 | `datacenter_heat_hourly` | **done (v1 scenarios)** |
| Hourly demand per building | `matching/hourly_demand.py` | Pod 3 | `building_hourly_demand` | **done** |
| Supply/demand metrics | `matching/metrics.py` | Pod 3 | — | **done** |
| Clustering | `matching/clustering.py` | Pod 3 | `clusters` | stub |
| Optimization | `matching/optimize.py` | Pod 3 | `matches`, `match_summary` | stub (formulation written) |
| Carbon / costs | `matching/economics.py` | Pod 3 | — | carbon done, costs need inputs |
| Map | `viz/map.py` | Pod 2 (weeks 5–6) | `outputs/maps/*.html` | stub |

Shared helpers: `config` (reads `config/settings.toml`), `units`, `timeutils`, `schemas`,
`io`, `metrics`, `crosswalk`.

## Docs

- [DELIVERABLES.md](DELIVERABLES.md): **what each person builds, week by week. Start here.**
- [docs/gaps.md](docs/gaps.md): what was missing from the scope doc and how it was filled
- [docs/decisions.md](docs/decisions.md): decisions D1–D15 (PMs to confirm)
- [docs/data_contract.md](docs/data_contract.md): every handoff table and its columns
- [docs/timeline.md](docs/timeline.md): weeks 3–6, per-person tasks
- [docs/datasets.md](docs/datasets.md): exact sources and paths
- [docs/plans/](docs/plans): models, data center heat, clustering/matching, map/economics
- [CONTRIBUTING.md](CONTRIBUTING.md): branches, PRs, data rules

## Repo layout

```
config/       settings.toml, datacenters.csv, building_type_crosswalk.csv
data/         raw/ interim/ processed/ sample/   (git-ignored; share via Drive)
docs/         gaps, decisions, contract, timeline, datasets, plans/
notebooks/    pod1_forecasting/ pod2_heat_demand/ pod3_matching/ pm/
outputs/      figures/ maps/ reports/            (git-ignored)
scripts/      downloads, run_pipeline, make_sample_data, gen_contract_doc
src/heatreuse/  the package (forecasting/, heat_demand/, matching/, viz/)
tests/        pytest
```
