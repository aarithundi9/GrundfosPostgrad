"""Rough carbon and cost numbers for the final deck.

Carbon (implemented): heat served by the data center displaces boiler fuel, but the heat
pump uses grid electricity.
    avoided = served_kwh / eff_fuel -> kBtu * fuel factor  -  hp_electricity_kwh * grid factor
Factors: LL97 2024-2029 coefficients in settings.economics (verify before citing).

Cost (stub): needs inputs that are not sourced yet (settings.economics.*_usd_*). The
function refuses to run while they are 0 so made-up numbers don't reach the deck.
"""

from __future__ import annotations

from heatreuse import config, units

FUEL_FACTOR_KEY = {
    "natural_gas": "tco2e_per_kbtu_natural_gas",
    "fuel_oil": "tco2e_per_kbtu_fuel_oil_2",
    "district_heating": "tco2e_per_kbtu_district_steam",
}


def co2_avoided_t(served_heat_kwh: float, heat_pump_electricity_kwh: float,
                  displaced_fuel: str = "natural_gas") -> float:
    e = config.load_settings()["economics"]
    eff = config.load_settings()["heat"]["efficiency"][displaced_fuel]
    fuel_kbtu = units.kwh_to_kbtu(served_heat_kwh / eff)
    avoided = fuel_kbtu * e[FUEL_FACTOR_KEY[displaced_fuel]]
    added = heat_pump_electricity_kwh * e["tco2e_per_kwh_electricity"]
    return float(avoided - added)


def rough_costs(pipe_length_m: float, heat_pump_kw: float, served_heat_kwh: float,
                heat_pump_electricity_kwh: float) -> dict:
    e = config.load_settings()["economics"]
    needed = ["pipe_cost_usd_per_m", "heat_pump_capex_usd_per_kw",
              "electricity_price_usd_per_kwh", "gas_price_usd_per_kbtu"]
    unset = [k for k in needed if not e.get(k)]
    if unset:
        raise ValueError(f"set these in config/settings.toml [economics] first (with a source): {unset}")
    raise NotImplementedError("TODO(Pod 3, week 6)")
