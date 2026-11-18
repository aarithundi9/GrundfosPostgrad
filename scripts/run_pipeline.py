"""Run pipeline steps in dependency order.

    python scripts/run_pipeline.py --list
    python scripts/run_pipeline.py profiles weather shares
    python scripts/run_pipeline.py --all

Each step reads contract tables from data/processed/ and writes its own. A step whose
code is still a stub prints "TODO" and the run stops there.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from heatreuse import config, io


def step_profiles():
    from heatreuse.forecasting import profiles
    io.write_table(profiles.build_hourly_profiles(), "hourly_profiles")


def step_weather():
    from heatreuse.forecasting import weather
    io.write_table(weather.build_weather_hourly(), "weather_hourly")


def step_shares():
    from heatreuse.forecasting import shares
    df = shares.shares_from_profiles(io.read_table("hourly_profiles"))
    shares.check_shares(df)
    io.write_table(df, "hourly_shares")


def step_features():
    from heatreuse.forecasting import features
    io.write_table(features.build_features(), "features_hourly")


def step_datacenter_heat():
    from heatreuse.matching import datacenter_heat
    df = datacenter_heat.build_datacenter_heat()
    io.write_table(df, "datacenter_heat_hourly")
    print(datacenter_heat.annual_summary(df).round(0).to_string(index=False))


def step_ll84():
    from heatreuse.heat_demand import ll84
    io.write_table(ll84.build_target(ll84.clean(ll84.load_raw())), "ll84_clean")


def step_study_area():
    from heatreuse.heat_demand import study_area
    io.write_table(study_area.build_study_area_buildings(config.get("study_area.anchor_datacenter")),
                   "study_area_buildings")


STEPS = {  # in dependency order
    "profiles": step_profiles,
    "weather": step_weather,
    "shares": step_shares,
    "features": step_features,
    "datacenter_heat": step_datacenter_heat,
    "ll84": step_ll84,
    "study_area": step_study_area,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("steps", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not (a.steps or a.all):
        print("steps:", ", ".join(STEPS))
        return
    for name in (list(STEPS) if a.all else a.steps):
        print(f"== {name}")
        try:
            STEPS[name]()
        except NotImplementedError:
            print(f"TODO: step '{name}' is not implemented yet; stopping.")
            sys.exit(1)


if __name__ == "__main__":
    main()
