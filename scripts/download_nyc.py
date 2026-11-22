"""Download LL84, PLUTO and Building Footprints from NYC Open Data (Socrata).

    python scripts/download_nyc.py            # all three
    python scripts/download_nyc.py ll84       # just one

Files go to data/raw/nyc/. Footprints and PLUTO are large (hundreds of MB): run once,
then share the Parquet outputs instead of re-downloading.

NOTE: dataset IDs come from the Week 1 table. Not tested from the cloud sandbox
(data.cityofnewyork.us was blocked there); if an ID 404s, open the dataset page and copy
the new 4x4 ID. PLUTO can also come from the NYC Planning MapPLUTO zip (release 26v1).
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from heatreuse import config

DATASETS = {
    "ll84": "5zyy-y8am",        # NYC Building Energy and Water Data Disclosure (LL84)
    "pluto": "64uk-42ks",       # Primary Land Use Tax Lot Output (PLUTO)
    "footprints": "5zhs-2jue",  # Building Footprints (has the_geom as WKT)
}


def download(name: str) -> None:
    dest = config.RAW / "nyc" / f"{name}.csv"
    if dest.exists():
        print(f"skip {dest} (exists)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://data.cityofnewyork.us/api/views/{DATASETS[name]}/rows.csv?accessType=DOWNLOAD"
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.writelines(r.iter_content(1 << 20))
    print(f"ok   {dest}")


if __name__ == "__main__":
    for n in (sys.argv[1:] or DATASETS):
        download(n)
