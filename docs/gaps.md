# Gap audit of the project scope doc (as of Nov 18, Week 3)

Each gap found in the scope doc and the Week 1–2 deliverables, how it is filled, and where.
"Decision" items are **proposed defaults**: PMs should confirm or change them in
[decisions.md](decisions.md), and the code follows whatever is in `config/settings.toml`.

## A. Staffing and schedule

| # | Gap | Fix | Where |
|---|-----|-----|-------|
| A1 | **Pod 3 (clustering + optimization) has no members** ("later"), yet it owns the data center heat estimate the whole matching step depends on. | Data center heat estimate is now built and runs (scenario model). Clustering/LP have full specs and stubs. **Staffing recommendation:** Pod 1 lists 4 names for 3 slots; Karan's weather step is the smallest and done by Week 3, so move Karan to Pod 3 from Week 4, with one PM backing. | `src/heatreuse/matching/`, `docs/plans/pod3_*.md`, [timeline.md](timeline.md) |
| A2 | Pod 1 says 3 people but lists 4 (Daksh, Emma, Karan, Lucent). | Resolved by A1. | — |
| A3 | Timeline weeks 3–6 are blank. | Filled in, with per-person tasks and Thanksgiving (Nov 26) accounted for. | [timeline.md](timeline.md) |
| A4 | Week 2 goal "heat output estimate for 111 8th Ave" was not done. | Done as a v1 scenario model: low/mid/high = 6.7 / 18 / 25 MW IT capacity from public listings. | `matching/datacenter_heat.py`, `config/datacenters.csv` |
| A5 | Week 1 Pod 3 dataset table and "what we learned" are empty. | Filled. | [plans/pod3_datacenter_heat.md](plans/pod3_datacenter_heat.md) |
| A6 | Open question "which other NYC data centers?" is unanswered. | Shortlist of 4 Manhattan carrier hotels added; capacities mostly unpublished, so they use default scenarios, flagged in the output. | `config/datacenters.csv` |
| A7 | No plan for the map or the cost/carbon section. | Map spec written (layers, inputs, outputs). Carbon calc implemented with LL97 factors. Cost calc refuses to run until real cost inputs are sourced. | `viz/map.py`, `matching/economics.py`, [plans/map_and_economics.md](plans/map_and_economics.md) |

## B. Cross-pod definitions (the biggest risk to the final numbers)

| # | Gap | Fix | Where |
|---|-----|-----|-------|
| B1 | **"Heat demand" undefined.** Emma and Rafa both asked if domestic hot water counts. | **D1:** heat = space heating + DHW, kept as separate columns. DHW is year-round, which is exactly what makes flat data center heat usable in summer. | decisions D1 |
| B2 | Fuel consumed vs heat delivered: Emma sums fuel (kWh), Rafa applies efficiencies. If the two pods differ, annual × hourly shares is inconsistent. | **D2:** one efficiency table in `settings.toml`, applied by both pods. | decisions D2 |
| B3 | Units: Pod 1 kWh, Pod 2 kBtu. | **D3:** kWh everywhere downstream; raw LL84 keeps `_kbtu`; `heatreuse.units` converts. | decisions D3, `units.py` |
| B4 | Timestamps: three names (`timestamp_hour`, `timestamp`, `timestamp_utc`) and Lucent's output says UTC while the data is EST. | **D4:** one column `timestamp`, tz-naive EST, hour-ending; `timestamp_local` only for calendar features. Verified against the actual NREL files: 35,040 15-min rows and 8,760 weather rows, both period-ending EST. Shared helpers plus tests. | decisions D4, `timeutils.py`, `tests/test_timeutils.py` |
| B5 | **No owner for the building-type mapping** (ComStock/ResStock ↔ LL84 property type ↔ PLUTO bldgclass). Without it, Pod 1's hourly shapes can't attach to Pod 2's buildings. | Crosswalk table + resolver, including size rules (small/medium/large office etc.) and a mixed-use blend. Neil applies it in `building_features`. | `config/building_type_crosswalk.csv`, `crosswalk.py` |
| B6 | Column names differ between the plans (`temperature` vs `temp_c`, etc.). | A single data contract for every handoff table, enforced on write. | [data_contract.md](data_contract.md), `schemas.py` |

## C. Method issues in the Week 2 plans

| # | Gap | Fix | Where |
|---|-----|-----|-------|
| C1 | **Lucent's "softmax'ed" hourly shares.** Softmax exponentiates kWh and destroys the shape. | Shares = value / annual sum. Implemented and tested. | `forecasting/shares.py` |
| C2 | **Lag features can't be used for buildings near the data center**: they have no metered hourly demand. Daksh's features include 24h/168h lags. | **D6:** Model A (weather + calendar, no lags) produces the profiles. Model B (with lags) is the short-term accuracy benchmark. Each gets its own baseline. | decisions D6, `forecasting/models.py`, `baseline.py` |
| C3 | Pod 3 would be blocked until Lucent's model is finished. | v1 shares come straight from the simulated 2018 profiles (available as soon as Emma's table exists). Model shares are v2. | `shares.py`, decisions D8 |
| C4 | **Validating on September only:** almost no heating, so it can't tune a heating model. | **D7:** leave-one-month-out CV inside Jan–Sep with a 168 h gap; Oct–Dec test unchanged. Implemented and tested. | `forecasting/splits.py` |
| C5 | Same-hour-last-week baseline needs lags; there was no baseline for the no-lag model. | Added a degree-hour climatology baseline. Oct–Dec months aren't in train, so a plain hour×month mean won't work. | `baseline.py` |
| C6 | Separate per-type GBMs on ~8,760 rows each, with some types built from very few models (hospital: 1). | One global model on heat *intensity* with `profile_type` as a feature; flag `models_used < 10`. | `models.py`, settings `min_models_used` |
| C7 | **Leakage / availability in Pod 2's features.** Rafa's plan lists water use as a feature, but non-reporters don't have LL84 fields. | Features restricted to PLUTO + footprints; leakage list in code. | `heat_demand/joins.py`, `model.py` |
| C8 | Raw annual kBtu target is heavily size-skewed (LL84 median 62k sqft vs 16k for missing-gas rows). | Predict log heat intensity (kWh/sqft), multiply by area; report error by size band. | `heat_demand/model.py` |
| C9 | Gas-for-heating share uses national EIA (68–69%). | Local per-building-type fractions from ComStock/ResStock (`fuel_heat_fractions`), EIA as fallback. | `profiles.py`, `ll84.py` |
| C10 | District steam isn't all heat (summer absorption chillers); "exclude steam buildings?" was open. | **D11:** keep steam buildings, flag `on_district_steam`, apply the heat fraction to steam too. | decisions D11 |
| C11 | Property-level LL84 heat → per-BIN predictions: split rule undecided. | Split by bldgarea share (fallback footprint × floors). | `joins.py` docstring |
| C12 | Year mismatch: profiles/weather are 2018, LL84 target is 2024. | Accept for v1 and list as a limitation. Optional HDD normalization using NOAA. | decisions D10 |
| C13 | "Which PUMA / is CD 4&5 enough?" (Emma) | 1 km around 111 8th Ave touches PUMAs 3807, 3808 and 3810. Use 3807 as primary, the other two as a sensitivity check. The download script supports both. | settings `[nrel]`, `download_nrel.py` |

## D. Data facts found while checking the actual files

1. **ResStock 2021 by-PUMA values are per dwelling unit**, not totals: multifamily 5+ in
   PUMA 3807 sums to ~12.8 MWh/yr site energy, i.e. per-unit scale. Multiply by
   `units_represented`. ComStock values are stock totals.
2. **ResStock 2025 has no by-PUMA files** (only by-state and others). Emma's choice of 2021 R1
   is the only PUMA-level residential option; its OEDI README marks it superseded.
3. ComStock 2025 R3 columns end in `.kwh`; ResStock 2021 columns have no suffix (still kWh).
4. ComStock fuel columns available for heat: natural_gas, fuel_oil, propane,
   district_heating, electricity × {heating, water_systems}. There is no `fans_heating`
   in ComStock (ResStock has it; it's excluded anyway).
5. Weather file `G3600610_2018.csv` is the same in the ComStock and ResStock releases;
   8,760 rows, ends at `2019-01-01 00:00`, which answers Karan's "last row" question.
6. Some PUMAs have extra ComStock types (3810 has `grocery`); the downloader tolerates 404s.
7. NYC Open Data couldn't be reached from the cloud sandbox, so the LL84 column names in
   `ll84.py` are from the plan and must be checked on first download.

## E. Still open: PM or Grundfos input needed

- Confirm D1–D14 (especially D1 heat definition and D6 Model A/B split).
- Assign Pod 3 (recommendation A1).
- Ask Grundfos (Ashley): realistic IT load / utilization for 111 8th Ave, typical
  heat-recovery supply temperatures, pipe and heat pump cost per unit for the deck,
  and feedback on the matching criteria (scope "Open questions").
- Cost inputs in `settings.toml [economics]`: each needs a cited source.
