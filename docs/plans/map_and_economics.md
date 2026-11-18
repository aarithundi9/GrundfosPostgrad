# Map and economics

## Interactive map (weeks 5–6; Rafa + Neil after Pod 2 tables are done)
Spec in `src/heatreuse/viz/map.py`. Built only from contract tables, so it can start
against `data/sample/` (`python scripts/make_sample_data.py`) before real results exist.
Folium; one HTML per data center plus a citywide view. Layers: data centers (size =
deliverable heat), buildings (color = annual heat, log scale), clusters (hulls), matches
(highlighted + lines), radius rings. Popups show the source of each number
(reported / predicted / scenario).

## Carbon (implemented)
`matching.economics.co2_avoided_t(served_kwh, hp_electricity_kwh, displaced_fuel)`:
avoided boiler fuel × LL97 factor − heat pump electricity × LL97 grid factor.
Present per scenario and per year. Note: the LL97 grid factor drops after 2030, so savings grow.

## Costs (needs sourced inputs)
`rough_costs` refuses to run until `settings.toml [economics]` has a cited value for pipe
cost per metre (Manhattan street works are expensive), heat pump capex per kW,
electricity price and gas price. Ask Grundfos for typical figures first. Until then, the
deck shows the "heat served vs pipe length" curve instead of dollars.
