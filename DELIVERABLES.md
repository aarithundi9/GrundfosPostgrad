# Deliverables: due Saturday Nov 28

The data is already loaded and cleaned. **Everyone builds their own model** on the same
dataset, scored the same way, and we see whose is best. Nobody waits on anybody.

## Setup (10 min)

```bash
git clone https://github.com/aarithundi9/GrundfosPostgrad.git
cd GrundfosPostgrad
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Read `data/modeling/README.md`. It explains every column and the rules. Work in a notebook
under `notebooks/<your pod folder>/`.

## Track A: hourly heat demand (Emma, Karan, Daksh, Lucent)

**Predict how much heat a building type uses in each hour**, from weather and calendar.
- Data: `data/modeling/hourly_heat.parquet` (17 building types × every hour of 2018)
- Train on Jan–Sep, predict Oct–Dec. Weather + calendar + building type only, no past demand.
- Baseline to beat: **0.392** mean CV(RMSE)

| Who | Suggested approach (pick something else if you want, just make it different) |
|---|---|
| Daksh | Regression: linear / polynomial on degree-hours + calendar, one per building type |
| Karan | Random forest |
| Lucent | Gradient boosting (LightGBM or XGBoost), one model across all types |
| Emma | Neural net (MLP or LSTM) |

## Track B: annual heat per building (Rafa, Neil, Vedant)

**Predict a building's yearly heat use from its PLUTO characteristics** (size, type, age, floors...).
This is how we estimate heat for buildings near the data center that don't report energy.
- Data: `data/modeling/building_heat_train.parquet`. Use rows with `label_quality_flag == "ok"`,
  train on `split == "train"`, predict `split == "test"`.
- Only PLUTO columns as features (list in the data README). LL84 columns would be cheating.
- Baseline to beat: **0.329** median % error

| Who | Suggested approach |
|---|---|
| Rafa | LASSO / linear regression on log(heat per sq ft) |
| Neil | Gradient boosting (LightGBM / XGBoost) |
| Vedant | Random forest, plus a breakdown of error by building size |

## What to turn in (everyone)

1. **Predictions file** in `submissions/`: `<yourname>_hourly.csv` or `<yourname>_buildings.csv`
   (format in the data README), then score it:
   `python scripts/score.py hourly submissions/<yourname>_hourly.csv` (or `buildings ...`)
2. **Your notebook**, pushed to the repo.
3. **A short write-up** (one paragraph or one slide): what you tried, your score, what
   helped most, and where your model is worst.

Push with `git pull`, `git add`, `git commit`, `git push`. Everyone writes different files,
so there shouldn't be conflicts. If `leaderboard.csv` conflicts, keep both lines.

## PMs (Aarit + Ishaan)
- Confirm the decisions in `docs/decisions.md` (especially: heat = heating + hot water).
- Email Grundfos: real power use at 111 8th Ave, usable water temperature, cost figures.
- After Saturday: pick the winning model per track. The building model then predicts heat
  for the ~8,450 lots near 111 8th Ave (`building_heat_predict.parquet`), and the hourly
  model gives each building its hourly pattern. That feeds the matching step.
