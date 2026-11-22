# Pod 3: Data center heat estimate (fills the Week 1 and Week 2 gaps)

## Week 1: research and datasets

| Dataset / source | Link | What is in it | Use |
|---|---|---|---|
| 111 8th Ave listings (Digital Realty JFK10, Lumen, Crown Castle, NTT, DataBank) | [Baxtel](https://baxtel.com/data-center/111-8th-digital-realty), [Datacentermap](https://www.datacentermap.com/usa/new-york/new-york/111-eight-avenue-dlr/specs), [Inflect](https://platform.inflect.com/building/111-8th-avenue-new-york/inap/datacenter/inap-111-eighth-avenue) | Power capacity per tenant / building: 6.7 MW utility (Baxtel), 18 MW (DLR JFK10), 24–25 MW building (Inflect), tenant suites 1–2 MW | Low / mid / high capacity scenarios |
| Other Manhattan carrier hotels | [DCD carrier hotel overview](https://datacenterdynamics.com/en/analysis/new-york-new-york-the-nyc-carrier-hotel-microcosm), [60 Hudson (DCF)](https://www.datacenterfrontier.com/colocation/article/11429666/datagryd-adds-data-center-capacity-at-60-hudson-street), [375 Pearl (Baxtel)](https://baxtel.com/data-center/sabey-intergate-manhattan) | 60 Hudson, 32 Avenue of the Americas, 375 Pearl, 325 Hudson. Mostly no published totals (DataGryd +5 MW at 60 Hudson; Sabey +3.6 MW at 375 Pearl) | Citywide run list (`config/datacenters.csv`) |
| NYC Local Law 97 carbon coefficients | 1 RCNY §103-14 | tCO2e per kWh electricity / kBtu gas, oil, steam (2024–2029) | Carbon savings |
| LBNL 2024 US Data Center Energy Usage Report | lbl.gov | PUE and utilization ranges for colocation | Sanity check for utilization/PUE |
| Heat reuse case studies (Stockholm Data Parks, Helsinki, Odense/Meta) | — | Supply temperatures, heat pump COPs, share of heat recovered | Parameter ranges |

**What we learned and how we can use it**
- No operator publishes metered heat. Capacity figures from aggregators vary 4× for the
  same building, so we model **scenarios**, not a point estimate (scope risk #1).
- Nearly all IT electricity becomes heat. Recoverable heat ≈ IT load × capture fraction.
  Air-cooled rooms give low-grade heat (~25–35 °C), so a heat pump is needed to reach
  hot-water temperatures (60–70 °C). Liquid-cooled racks (45–60 °C) need little lift.
- IT load is nearly flat over the day and year; building demand is very seasonal. That
  mismatch is the core finding to quantify (`matching.metrics.seasonal_coincidence`).
- Capacity ≠ load: colocation sites run well below nameplate (assume 60%).

## Week 2-style plan

| Part | Plan |
|---|---|
| Input | `config/datacenters.csv` (capacity scenarios + sources), `settings.toml [datacenter]` parameters |
| Steps | IT load = capacity × utilization × small diurnal shape → recoverable = × capture → heat pump COP = 0.5 × T_sup/(T_sup − T_src) → deliverable = recoverable × COP/(COP−1), HP electricity = deliverable/COP. Hourly for 2018 (8,760 h). |
| Output | `datacenter_heat_hourly`: dc_id, scenario, timestamp, it_load_kwh, recoverable_heat_kwh, deliverable_heat_kwh, heat_pump_electricity_kwh (+ capacity_mw, capacity_is_default) |
| Tools | pandas, numpy (done: `src/heatreuse/matching/datacenter_heat.py`) |
| Open questions | Real utilization and cooling type at 111 8th Ave (ask Grundfos); supply temperature the buildings can use (older steam/high-temp radiator buildings need more lift than DHW). |

## Current numbers (v1, 111 8th Ave)

| Scenario | IT capacity | Deliverable heat | Heat pump electricity |
|---|---|---|---|
| low | 6.7 MW | ~35,500 MWh/yr (~4.1 MW avg) | ~7,400 MWh/yr |
| mid | 18 MW | ~95,400 MWh/yr (~10.9 MW avg) | ~19,800 MWh/yr |
| high | 25 MW | ~132,600 MWh/yr (~15.1 MW avg) | ~27,400 MWh/yr |

Reproduce: `python scripts/run_pipeline.py datacenter_heat`. Sensitivity worth showing:
utilization 0.4–0.8, source temperature 30 °C (air) vs 50 °C (liquid).
