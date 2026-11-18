# How we work

1. **Branch per task:** `git checkout -b <yourname>/<topic>` (e.g. `emma/hourly-profiles`).
2. **Code goes in `src/heatreuse/`**, exploration in `notebooks/<pod>/`. When a notebook
   works, move the logic into the module that has your name on it, so others can import it.
3. **Hand off through contract tables only.** Write with `heatreuse.io.write_table(df, name)`.
   It checks your columns against `docs/data_contract.md`. Need a new column or table?
   Edit `src/heatreuse/schemas.py`, run `python scripts/gen_contract_doc.py`, mention it in your PR.
4. **Never commit data** (CSV/Parquet/zip) or notebook outputs. Run `nbstripout --install` once.
   Share processed Parquet files on the team Drive under the same filename.
5. **Before a PR:** `pytest -q` passes. Add a test if you wrote a function others depend on.
6. **PR to `main`**, one reviewer from your pod (or a PM). Keep PRs small, ideally one per week per person.
7. **Assumptions** (a number you picked, a filter you applied) go in `docs/decisions.md`.
8. **Units and time:** kWh, `_kwh` suffix; `timestamp` is tz-naive EST hour-ending. Use
   `heatreuse.units` and `heatreuse.timeutils` rather than doing it by hand.
