"""Download NREL ComStock, ResStock and weather files from the public OEDI bucket.

    python scripts/download_nrel.py                 # primary PUMA (3807) + weather
    python scripts/download_nrel.py --sensitivity   # also PUMAs 3808 and 3810

No login needed. Files go to data/raw/nrel/{comstock,resstock,weather}/. Re-running
skips files that already exist. ~4 MB per ComStock file, ~16 MB per ResStock file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from heatreuse import config


def urls(pumas: list[str]) -> list[tuple[str, Path]]:
    n = config.load_settings()["nrel"]
    base, raw = n["oedi_base"], config.RAW / "nrel"
    out = []
    for puma in pumas:
        p = puma.lower()
        for t in n["comstock_types"]:
            url = (f"{base}/{n['comstock_release']}/timeseries_aggregates/by_puma/"
                   f"upgrade=0/puma={puma}/up0-{p}-{t}.csv")
            out.append((url, raw / "comstock" / f"{puma}_{t}.csv"))
        for t in n["resstock_types"]:
            url = (f"{base}/{n['resstock_release']}/timeseries_aggregates/by_puma/"
                   f"state=NY/{p}-{t}.csv")
            out.append((url, raw / "resstock" / f"{puma}_{t}.csv"))
    county = n["weather_county"]
    out.append((f"{base}/{n['comstock_release']}/weather/amy2018/{county}_2018.csv",
                raw / "weather" / f"{county}_2018.csv"))
    for name in ["data_dictionary.tsv", "enumeration_dictionary.tsv"]:
        out.append((f"{base}/{n['comstock_release']}/{name}", raw / "comstock" / name))
        out.append((f"{base}/{n['resstock_release']}/{name}", raw / "resstock" / name))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensitivity", action="store_true", help="also download nearby PUMAs")
    args = ap.parse_args()
    n = config.load_settings()["nrel"]
    pumas = [n["primary_puma"]] + (n["sensitivity_pumas"] if args.sensitivity else [])
    missing = []
    for url, dest in urls(pumas):
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=120)
        if r.status_code == 404:
            missing.append(url)  # not every PUMA has every building type
            continue
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"ok   {dest.relative_to(config.ROOT)}")
    for u in missing:
        print(f"404  {u}  (type not simulated in this PUMA)")


if __name__ == "__main__":
    main()
