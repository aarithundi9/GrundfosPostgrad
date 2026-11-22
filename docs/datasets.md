# Datasets

| Dataset | Exact source | Download | Owner | Notes |
|---|---|---|---|---|
| NREL ComStock 2025 R3 (AMY2018), by PUMA | `s3://oedi-data-lake/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/comstock_amy2018_release_3/timeseries_aggregates/by_puma/upgrade=0/puma=G36003807/up0-g36003807-<type>.csv` | `scripts/download_nrel.py` | Emma | 15-min, EST period-ending, stock totals in kWh. 14 types in PUMA 3807 |
| NREL ResStock 2021 R1 (AMY2018), by PUMA | `.../2021/resstock_amy2018_release_1/timeseries_aggregates/by_puma/state=NY/g36003807-<type>.csv` | `scripts/download_nrel.py` | Emma | **Per dwelling unit**; × `units_represented`. Only release with by-PUMA files |
| NREL AMY2018 weather, New York County | `.../2025/comstock_amy2018_release_3/weather/amy2018/G3600610_2018.csv` | `scripts/download_nrel.py` | Karan | 8,760 rows, hour-ending EST. The exact weather used in the simulations |
| NOAA LCD/ISD, Central Park (KNYC) 2018 | NOAA NCEI Local Climatological Data | manual | Karan | Validation only |
| Copernicus ERA5 hourly 2018 | CDS `reanalysis-era5-single-levels-timeseries` | manual (CDS account) | Lucent | Weather-source sensitivity (optional) |
| NYC LL84 Energy & Water Disclosure | NYC Open Data `5zyy-y8am` | `scripts/download_nyc.py ll84` | Rafa | Filter Calendar Year 2024 |
| NYC PLUTO 26v1 | NYC Open Data `64uk-42ks` or NYC Planning MapPLUTO zip | `scripts/download_nyc.py pluto` | Neil | Features for every lot |
| NYC Building Footprints | NYC Open Data `5zhs-2jue` | `scripts/download_nyc.py footprints` | Vedant | Geometry, BIN, height |
| Data center capacities | Aggregator listings (see `config/datacenters.csv`) | — | Pod 3 | Scenario inputs, not official |
| LL97 carbon coefficients | 1 RCNY §103-14 | — | Pod 3 | In `settings.toml [economics]` |

Manhattan 2010 PUMAs near 111 8th Ave: **3807** Chelsea/Clinton/Midtown (CD 4–5, primary),
3808 Murray Hill/Gramercy/Stuyvesant Town (CD 6), 3810 Battery Park City/Greenwich
Village/SoHo (CD 1–2).
