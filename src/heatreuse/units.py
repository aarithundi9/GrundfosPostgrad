"""Unit conversions. Canonical unit everywhere downstream is kWh (decision D3)."""

from __future__ import annotations

KWH_PER_KBTU = 0.29307107       # 1 kBtu = 0.293 kWh
KBTU_PER_KWH = 1 / KWH_PER_KBTU  # 1 kWh = 3.412 kBtu
KWH_PER_THERM = 29.307107
KWH_PER_MMBTU = 293.07107
FT_PER_M = 3.28084
SQFT_PER_M2 = 10.7639


def kbtu_to_kwh(x):
    return x * KWH_PER_KBTU


def kwh_to_kbtu(x):
    return x * KBTU_PER_KWH


def m_to_ft(x):
    return x * FT_PER_M


def ft_to_m(x):
    return x / FT_PER_M


def mw_to_kw(x):
    return x * 1000.0
