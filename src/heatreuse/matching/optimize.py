"""OWNER: Pod 3. Choose which buildings to connect -> ``matches`` + ``match_summary``.

Formulation (mixed-integer LP, PuLP + CBC; full write-up in
docs/plans/pod3_clustering_matching.md):

  Sets      b in candidate buildings, t in periods (576 representative hours, weight w_t)
  Data      D[b,t] demand kWh, S[t] deliverable data center heat kWh,
            L[b] pipe length m = routing_factor * distance_m, c_pipe $/m (optional)
  Vars      x[b] in {0,1} connect;  q[b,t] >= 0 heat served
  Max       sum_t w_t * sum_b q[b,t]  -  lambda * sum_b c_pipe * L[b] * x[b]
  s.t.      q[b,t] <= D[b,t] * x[b]            (only serve connected buildings)
            sum_b q[b,t] <= S[t]               (data center capacity, every period)
            L[b] * x[b] <= max_pipe_length_m   (feasible distance)
            optional: sum_b L[b] x[b] <= pipe budget; min coverage per connected bldg

Start with lambda = 0 and a pipe budget (no cost data yet), then add costs in week 6.
Benchmarks to beat: greedy by demand (biggest first) and greedy by distance (closest first).
"""

from __future__ import annotations

import pandas as pd


def greedy_baseline(buildings: pd.DataFrame, demand, supply, order_by: str = "distance_m"):
    """Connect buildings in order until supply is used up. TODO(Pod 3)."""
    raise NotImplementedError


def solve_matching(buildings: pd.DataFrame, demand, supply, weights,
                   pipe_budget_m: float | None = None, lam: float = 0.0):
    """TODO(Pod 3)."""
    raise NotImplementedError
