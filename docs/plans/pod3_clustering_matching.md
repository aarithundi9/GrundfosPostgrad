# Pod 3: Clustering and matching

## Inputs
- `study_area_buildings` (Vedant): annual heat per BIN, location, type.
- `hourly_shares` (Emma v1 / Lucent v2).
- `datacenter_heat_hourly` (above).

## Steps
1. **Hourly demand per building:** `matching.hourly_demand.demand_matrix` (done).
2. **Clusters** (`clustering.py`): DBSCAN on centroids in EPSG:2263, eps 150 m,
   min_samples 3, weighted by annual heat. Per-cluster summary + coincidence with supply.
3. **Baselines** (`optimize.greedy_baseline`): connect largest-first, and nearest-first,
   until the hourly supply is used up.
4. **MILP** (`optimize.solve_matching`, PuLP/CBC) on 576 representative periods
   (`matching.metrics.representative_days`, done):

   - maximize Σ_t w_t Σ_b q_bt − λ Σ_b c·L_b·x_b
   - q_bt ≤ D_bt·x_b; Σ_b q_bt ≤ S_t; L_b·x_b ≤ max length; optional pipe budget Σ L_b x_b ≤ B
   - L_b = 1.3 × distance_m (Manhattan routing)

   Start with λ = 0 and sweep the pipe budget B (e.g. 1, 2, 5, 10 km). That gives a
   "heat served vs pipe built" curve, which is the most useful chart for Grundfos
   while cost data is missing.
5. **Score** with `matching.metrics.coincidence` and `seasonal_coincidence`: demand
   coverage, supply utilization, short hours, by month.
6. Write `matches` (per building) and `match_summary` (per DC × scenario, with
   `co2_avoided_t` from `economics.co2_avoided_t`).

## Outputs
`clusters`, `matches`, `match_summary` (see data_contract.md).

## Tools
scikit-learn (DBSCAN), PuLP, geopandas/shapely, numpy.

## Open questions / risks
- Are buildings on district steam realistic connections? (D11: keep them and report separately.)
- "Good match" has no labels (scope risk). The objective encodes it: heat actually used,
  hour by hour, within a pipe budget. Ask Grundfos if they'd weight anything else
  (e.g. prefer a few large anchor customers).
- If 8,760 h is needed, solve the LP relaxation first, fix x, then re-solve q hourly.
