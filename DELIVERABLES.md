# Deliverables

Find your name, do your part, push your code. Everyone works in their **own file**,
so you won't step on each other.

## Getting started (once, ~10 min)

```bash
git clone https://github.com/aarithundi9/GrundfosPostgrad.git
cd GrundfosPostgrad
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then open your file (listed below). It already has the function names and the steps
written out in comments. Replace each `raise NotImplementedError` with your code.

**Each time you work:** `git pull` first. When done: `git add`, `git commit`, `git push`.
Don't commit data files (CSVs, Parquet). They're ignored automatically.

**Three rules that keep everyone's pieces compatible**
1. Energy is in **kWh**. Name columns with the unit, e.g. `heat_total_kwh`.
2. Time column is called `timestamp`, Eastern Standard Time, no timezone attached.
   Use the helpers in `src/heatreuse/timeutils.py` and don't do it by hand.
3. Save your output table with `io.write_table(df, "<table name>")`. It tells you if a
   column is missing. Load someone else's with `io.read_table("<table name>")`.

---

## Due Sun Nov 30: get the data in, first models

(Thanksgiving is Thursday, so this week is about the same size as a normal week.)

### Emma: hourly building heat profiles
- **File:** `src/heatreuse/forecasting/profiles.py`
- **Do:** run `python scripts/download_nrel.py`, then load the ComStock and ResStock files
  for Chelsea (PUMA 3807). For each building type, add up heating + hot water,
  turn 15-minute rows into hourly rows, and save.
- **Watch out:** ResStock numbers are *per apartment*, so multiply by `units_represented`.
- **Output:** `hourly_profiles` table (and `fuel_heat_fractions` for Rafa)
- **Done when:** `python scripts/run_pipeline.py profiles shares` runs, 8,760 rows per building type.

### Karan: weather
- **File:** `src/heatreuse/forecasting/weather.py`
- **Do:** load the NREL 2018 Manhattan weather file (downloaded by Emma's script), rename
  columns, check for gaps/bad values, add heating degree-hours, 24 h rolling average, and
  1 h / 3 h lagged temperature. Then compare against NOAA Central Park 2018.
- **Output:** `weather_hourly` table
- **Done when:** `python scripts/run_pipeline.py weather` runs; NOAA correlation ≥ 0.95.

### Daksh: features and baselines
- **Files:** `src/heatreuse/forecasting/features.py`, `baseline.py`
- **Do:** join Emma's and Karan's tables on `timestamp`. Add hour, day of week, month,
  weekend, holiday, and demand from 24 h and 168 h earlier. Build two baselines:
  "same hour last week", and a simple temperature-based one.
- **Output:** `features_hourly` table + baseline predictions
- **Done when:** a table of baseline error (MAE) per building type for Oct–Dec.
- **Tip:** you can start once Emma pushes even a rough version of her table.

### Lucent: gradient boosting model
- **File:** `src/heatreuse/forecasting/models.py` (plan: `docs/plans/pod1_models.md`)
- **Do:** train one LightGBM model across all building types, using weather + calendar
  only (no past-demand columns). That's "Model A". Tune it by holding out one month at a
  time (`splits.month_folds`, already written).
- **Output:** cross-validation scores for Model A
- **Done when:** you have Model A scores. Don't touch the Oct–Dec test data yet.

### Rafa: LL84 heat target
- **File:** `src/heatreuse/heat_demand/ll84.py`
- **Do:** run `python scripts/download_nyc.py ll84`. **First check the column names** in
  the download match the `RENAME` list at the top of the file (I couldn't verify them).
  Clean 2024 data, then compute each building's annual heat = gas + oil + steam +
  hot water, adjusted by the heating share and boiler efficiency (formula in the file).
- **Output:** `ll84_clean` table
- **Done when:** you can say how many buildings have a usable heat number.

### Neil: joining LL84, PLUTO and footprints
- **File:** `src/heatreuse/heat_demand/joins.py`
- **Do:** download PLUTO and footprints (`python scripts/download_nyc.py pluto footprints`).
  Clean the BBL/BIN keys (helpers `norm_bbl` and `norm_bin` are already written) and link
  the three datasets.
- **Output:** `bbl_bin_crosswalk` table + match rates (what % of LL84 buildings found a match)
- **Done when:** match rates by borough are written down.

### Vedant: buildings around 111 8th Ave
- **Files:** `src/heatreuse/heat_demand/study_area.py`, `model.py`
- **Do:** using the footprints, find every building within 500 m, 1 km and 2 km of 111 8th
  Ave (measured from the building's edge). Write the simple estimate:
  floor area × typical heat per sq ft for that building type.
- **Output:** first draft of `study_area_buildings`
- **Done when:** you know how many buildings are in each radius.

### Aarit + Ishaan (PMs)
- Read `docs/decisions.md` and confirm or change the 15 decisions (especially:
  heat = heating + hot water).
- Decide who owns Pod 3 (suggestion: Karan + one PM from Week 5).
- Email Grundfos: real power use at 111 8th Ave, usable water temperature, cost figures.

---

## Due Sun Dec 7: full answer for 111 8th Ave

| Who | Deliverable |
|---|---|
| Lucent | Model A + Model B (adds past demand) scored on Oct–Dec once; hourly shares from Model A |
| Daksh | Error charts: by building type, by month, at peak hours |
| Emma | Compare profiles from neighboring areas (PUMAs 3808, 3810). Do they look different? |
| Rafa | ML model (LASSO + LightGBM) predicting heat per sq ft for buildings that don't report |
| Neil | `building_features`: one row per building with features and building type |
| Vedant | Simple vs ML model accuracy by building size; final `study_area_buildings` |
| Pod 3 | Clustering (`matching/clustering.py`) and choosing which buildings to connect (`matching/optimize.py`). Plan in `docs/plans/pod3_clustering_matching.md` |

## Due Sun Dec 14: other data centers, map, presentation

| Who | Deliverable |
|---|---|
| Rafa + Neil | Interactive map (`viz/map.py`). Can start early with fake data: `python scripts/make_sample_data.py` |
| Vedant + Pod 3 | Run the same pipeline on the other data centers (cut first if behind) |
| Pod 3 | Carbon savings per scenario (`matching/economics.py`, already written) |
| Pod 1 | One results slide: baseline vs gradient boosting (vs LSTM if done) |
| Everyone | Clean up your file, make sure `pytest` passes |
| PMs | Final presentation |

---

**Stuck?** Each file's top comment has the full step list. Background is in `docs/`:
`gaps.md` (why things changed from the Week 2 plans), `data_contract.md` (every table's
columns), `datasets.md` (where data comes from).
