# Decision log

Status: **Proposed**. PMs confirm or change each decision; flip it to *Accepted* with a date.
Values live in `config/settings.toml`, so changing a decision means changing one line there.
New decisions get the next number and go at the bottom.

| ID | Decision | Why | Status |
|----|----------|-----|--------|
| D1 | **Heat demand = space heating + domestic hot water (DHW)**, stored as `space_heating_kwh`, `dhw_kwh`, `heat_total_kwh`. Fans, pumps, hot tubs, pools excluded. | Data center heat is flat all year; DHW is the only year-round heat sink, so leaving it out would make summer matching look useless. LL84 can't separate the two anyway. | Proposed |
| D2 | **Fuel → delivered heat** via one efficiency table (gas/oil/propane 0.80, district 1.00, electric 1.00, wood 0.65), used by both pods. | Pod 1's hourly shapes and Pod 2's annual totals must mean the same thing. Electric heating at 1.0 is conservative; heat pumps would be higher (sensitivity check). | Proposed |
| D3 | **kWh is the canonical unit.** Columns end in their unit (`_kwh`, `_kbtu`, `_m`, `_sqft`). | Pods 1 and 2 used different units. | Proposed |
| D4 | **Time:** `timestamp` = tz-naive EST, hour-ending, 8,760 rows (2018-01-01 01:00 → 2019-01-01 00:00). `timestamp_local` (NY wall clock) only for calendar features. | Matches NREL files exactly (checked). Avoids DST gaps and duplicates in joins. | Proposed |
| D5 | **Building type crosswalk** in `config/building_type_crosswalk.csv`, resolved by `heatreuse.crosswalk`. Office size bands <25k / 25–150k / ≥150k sqft; hotel <75k; school <100k. Mixed-use blends residential and commercial by `res_share`. | No one owned this link between pods. | Proposed |
| D6 | **Two forecasting models.** Model A: weather + calendar + building type, no lags → used for profiles. Model B: plus demand lags → short-term accuracy benchmark. One global model on heat intensity rather than per-type models. | Buildings near the data center have no metered demand to lag. Some types have few simulated models. | Proposed |
| D7 | **Split:** train Jan–Sep, test Oct–Dec (unchanged). Tune with leave-one-month-out CV inside Jan–Sep (168 h gap), not September alone. | September has almost no heating demand. | Proposed |
| D8 | **Hourly shares** = value / annual sum (not softmax). v1 from the simulated 2018 profiles; v2 from Model A. | Unblocks Pod 3 now; softmax distorts the shape. | Proposed |
| D9 | **Study area:** 1 km from the data center footprint edge (EPSG:2263), sensitivity 500 m and 2 km. | Keeps Vedant's plan. Pipe length uses a 1.3× Manhattan routing factor. | Proposed |
| D10 | **LL84 calendar year 2024** as the annual target, against 2018 profiles. Year mismatch accepted for v1 and listed as a limitation; optional HDD normalization with NOAA. | Most recent data, and the weather difference is second-order for ranking buildings. | Proposed |
| D11 | **Keep district-steam buildings**, flagged `on_district_steam`. Apply the ComStock heat fraction to steam (some is summer cooling). | Steam buildings are heavy heat users; whether converting them is feasible is for the matching and the deck to decide. | Proposed |
| D12 | **Pod 2 target:** log annual heat intensity (kWh/sqft). Features from PLUTO + footprints only. Grouped holdout by `split_group_id`. | Size skew, leakage, multi-building properties. | Proposed |
| D13 | **No data in git.** Raw data is re-downloadable via `scripts/`. Processed Parquet tables are shared on the team Drive under the same filenames. | Keeps the repo small; makes the contract the interface. | Proposed |
| D14 | **Data center heat is a scenario model** (low/mid/high capacity × utilization 0.6 × capture 0.8; heat pump from 30 °C to 65 °C at 50% of Carnot COP ≈ 4.8). | No public metered data, as the scope's risk section says. | Proposed |
| D15 | **Optimization on representative days** (12 months × weekday/weekend × 24 h = 576 periods, weighted). Move to 8,760 h only if it solves quickly. | Keeps the MILP small enough for CBC with hundreds of candidate buildings. | Proposed |
| D16 | **`weather_hourly`'s first-hour lag/rolling features are back-filled, not left `NaN`.** `temp_c_roll24` uses an expanding mean for the first 23 rows (`min_periods=1`); `temp_c_lag1`/`temp_c_lag3` back-fill their first 1–3 rows from hour 1's own reading. | The contract requires these columns populated for every row; `NaN` would propagate into `features_hourly` and break any model that doesn't explicitly drop the first day. Only 1–3 of 8,760 rows are affected either way. | Proposed |
