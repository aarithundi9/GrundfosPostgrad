import pandas as pd
import pytest

from heatreuse import crosswalk, schemas, units


def test_every_table_has_keys_in_required():
    for t in schemas.TABLES.values():
        assert set(t.keys) <= set(t.required), t.name


def test_validate_reports_missing():
    with pytest.raises(ValueError, match="missing required"):
        schemas.validate(pd.DataFrame({"timestamp": []}), "hourly_shares")


def test_units_roundtrip():
    assert units.kwh_to_kbtu(units.kbtu_to_kwh(123.0)) == pytest.approx(123.0)
    assert units.kwh_to_kbtu(1) == pytest.approx(3.412, rel=1e-3)


def test_crosswalk_targets_are_valid():
    cw = crosswalk.load_crosswalk()
    concrete = cw.loc[~cw["profile_type"].str.startswith("@") & (cw["profile_type"] != "EXCLUDE"),
                      "profile_type"]
    assert set(concrete) <= crosswalk.valid_profile_types()


@pytest.mark.parametrize("src,val,kw,expected", [
    ("ll84", "Office", {"floor_area_sqft": 500_000}, "largeoffice"),
    ("ll84", "Office", {"floor_area_sqft": 60_000}, "mediumoffice"),
    ("ll84", "Multifamily Housing", {"units_res": 120}, "multi-family_with_5plus_units"),
    ("ll84", "Hotel", {"floor_area_sqft": 30_000}, "smallhotel"),
    ("pluto", "D4", {}, "multi-family_with_5plus_units"),
    ("pluto", "I1", {}, "hospital"),
    ("pluto", "G1", {}, "EXCLUDE"),
    ("ll84", "Other", {"bldgclass": "O4", "floor_area_sqft": 200_000}, "largeoffice"),
])
def test_resolve(src, val, kw, expected):
    assert crosswalk.resolve(src, val, **kw) == expected
