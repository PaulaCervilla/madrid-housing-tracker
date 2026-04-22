"""Tests for the affordability calculator."""
from __future__ import annotations

import pandas as pd

from src.transformers import affordability, cleaner


def _make_index(start: int, end: int, base_value: float, growth: float,
                col: str) -> pd.DataFrame:
    rows = []
    for i, year in enumerate(range(start, end + 1)):
        rows.append({
            "date": pd.Timestamp(year=year, month=1, day=1),
            "region": "Madrid, Comunidad de",
            col: base_value * (1 + growth) ** i,
        })
    return pd.DataFrame(rows)


def test_affordability_table_basic_shape():
    hpi   = _make_index(2015, 2024, 100.0, 0.05, "hpi")
    rpi   = _make_index(2015, 2024, 100.0, 0.04, "rpi")
    cpi   = _make_index(2015, 2024, 100.0, 0.02, "cpi")
    wages = _make_index(2015, 2024, 30000.0, 0.01, "wage_eur")

    aff = affordability.build_affordability_table(hpi, rpi, wages, cpi)

    assert not aff.empty
    assert {"price_per_m2", "price_to_income", "years_to_down_payment",
            "rent_burden"}.issubset(aff.columns)

    # 2015 is the anchor → price_per_m2 must equal the configured anchor.
    row_2015 = aff[aff["year"] == 2015].iloc[0]
    assert round(row_2015["price_per_m2"], 2) == 2400.00

    # Prices grew faster than wages → price_to_income should rise.
    pti = aff.set_index("year")["price_to_income"]
    assert pti.loc[2024] > pti.loc[2015]


def test_filter_region_matches_madrid_variants():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-01"]),
        "region": ["Madrid, Comunidad de", "Cataluña", "Comunidad de Madrid"],
        "value": [1, 2, 3],
    })
    out = cleaner.filter_region(df, "Madrid, Comunidad de")
    assert sorted(out["value"].tolist()) == [1, 3]
