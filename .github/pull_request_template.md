## What this does
<!-- one or two sentences; which pipeline step / table -->

## Contract
- [ ] Output table matches `docs/data_contract.md` (written via `heatreuse.io.write_table`)
- [ ] Timestamps are tz-naive EST hour-ending (`heatreuse.timeutils`)
- [ ] Energy columns in kWh with `_kwh` suffix

## Checks
- [ ] `pytest -q` passes
- [ ] No data files or notebook outputs committed
- [ ] Open questions / assumptions added to `docs/decisions.md` if any
