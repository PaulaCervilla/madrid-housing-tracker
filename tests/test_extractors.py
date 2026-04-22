"""Tests for the INE extractor — JSON-stat parsing logic."""
from __future__ import annotations

from src.extractors import ine


def test_jsonstat_to_long_simple():
    payload = {
        "id": ["Region", "Periodo"],
        "size": [2, 3],
        "dimension": {
            "Region": {
                "category": {
                    "index": {"ES": 0, "MD": 1},
                    "label": {"ES": "Nacional", "MD": "Madrid, Comunidad de"},
                }
            },
            "Periodo": {
                "category": {
                    "index": {"2020": 0, "2021": 1, "2022": 2},
                    "label": {"2020": "2020", "2021": "2021", "2022": "2022"},
                }
            },
        },
        # Order: ES/2020, ES/2021, ES/2022, MD/2020, MD/2021, MD/2022
        "value": [100.0, 102.0, 105.0, 110.0, 115.0, None],
    }
    df = ine._jsonstat_to_long(payload)
    assert len(df) == 5  # the None is dropped
    assert set(df.columns) == {"region", "periodo", "value"}
    madrid_2021 = df[(df["region"] == "Madrid, Comunidad de") &
                     (df["periodo"] == "2021")]
    assert madrid_2021["value"].iloc[0] == 115.0


def test_parse_period_handles_all_formats():
    assert ine._parse_period("2024").year == 2024
    assert ine._parse_period("2024T2").month == 4
    assert ine._parse_period("2024M03").month == 3
    assert ine._parse_period("garbage") is None
