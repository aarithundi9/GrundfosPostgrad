import numpy as np
import pandas as pd
import pytest

from heatreuse import timeutils
from heatreuse.matching import datacenter_heat, economics, hourly_demand, metrics


def test_cop_reasonable():
    cop = datacenter_heat.heat_pump_cop(30, 65, 0.5)
    assert 4 < cop < 6


def test_energy_balance():
    df = datacenter_heat.hourly_heat(18)
    assert len(df) == 8760
    np.testing.assert_allclose(df["deliverable_heat_kwh"],
                               df["recoverable_heat_kwh"] + df["heat_pump_electricity_kwh"])
    # 18 MW x 0.6 util x 0.8 capture ~ 75.7 GWh recoverable per year
    assert df["recoverable_heat_kwh"].sum() == pytest.approx(18_000 * 0.6 * 0.8 * 8760, rel=1e-3)


def test_build_all_sites_has_scenarios():
    df = datacenter_heat.build_datacenter_heat()
    assert set(df["scenario"]) == {"low", "mid", "high"}
    anchor = df[df["dc_id"] == "dc_111_8th_ave"]
    assert not anchor["capacity_is_default"].any()


def test_coincidence():
    m = metrics.coincidence([10, 10, 10], [5, 10, 20])
    assert m["served_heat_kwh"] == 25
    assert m["demand_coverage"] == pytest.approx(25 / 35)
    assert m["supply_utilization"] == pytest.approx(25 / 30)
    assert m["hours_supply_short"] == 1


def test_representative_days_preserve_energy():
    ts = timeutils.canonical_index(2018)
    v = np.random.default_rng(1).uniform(size=(2, len(ts)))
    periods, means, w = metrics.representative_days(ts, v)
    assert len(periods) == 576 and w.sum() == 8760
    np.testing.assert_allclose((means * w).sum(axis=1), v.sum(axis=1))


def test_hourly_demand_matches_annual():
    ts = timeutils.canonical_index(2018)
    sh = pd.concat([pd.DataFrame({"profile_type": p, "source": "simulated_2018", "timestamp": ts,
                                  "hourly_share": 1 / len(ts)})
                    for p in ["largeoffice", "multi-family_with_5plus_units"]])
    b = pd.DataFrame({"bin": ["1000001", "1000002"], "profile_type": ["largeoffice", "largeoffice"],
                      "res_share": [0.0, 0.5], "annual_heat_kwh": [1e6, 2e6]})
    m, _, _ = hourly_demand.demand_matrix(b, sh)
    np.testing.assert_allclose(m.sum(axis=1), [1e6, 2e6])
    w = hourly_demand.profile_weights(b)
    assert w.groupby("bin")["weight"].sum().tolist() == [1.0, 1.0]


def test_co2_positive_for_gas_displacement():
    t = economics.co2_avoided_t(1_000_000, 200_000)
    assert t > 0


def test_costs_refuse_without_inputs():
    with pytest.raises(ValueError):
        economics.rough_costs(100, 1000, 1e6, 2e5)
