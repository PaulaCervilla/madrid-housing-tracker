"""Extractor for INE (Instituto Nacional de Estadística) tables.

The INE exposes a free, no-auth REST API:

    https://servicios.ine.es/wstempus/jsstat/ES/DATOS_TABLA/{table_id}

Each table is returned in JSON-stat 2.0 format.  The structure has:
- "dimension" — definitions of every dimension (region, period, indicator…)
- "value"     — flat array of observations, ordered by the cartesian product
                of dimension indices in the order given by "id".
- "size"      — list with the cardinality of every dimension.

This module flattens that structure into a tidy long DataFrame with one row
per observation and one column per dimension.
"""
from __future__ import annotations

import logging
from itertools import product
from typing import Any

import pandas as pd

import config
from src.extractors.http_client import http_get_json

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic JSON-stat → tidy DataFrame
# ---------------------------------------------------------------------------


def _jsonstat_to_long(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert a JSON-stat 2.0 dataset into a long DataFrame."""
    dim_ids: list[str] = payload["id"]
    sizes: list[int] = payload["size"]
    values: list = payload["value"]
    dims: dict[str, dict] = payload["dimension"]

    # For each dimension, build an ordered list of category labels.
    label_lists: list[list[str]] = []
    for d in dim_ids:
        cat = dims[d]["category"]
        # "index" maps code -> position; "label" maps code -> human label.
        index_map: dict[str, int] = cat["index"]
        labels: dict[str, str] = cat.get("label", {})
        # Sort codes by their position so we get them in the dataset's order.
        ordered_codes = sorted(index_map.keys(), key=lambda c: index_map[c])
        label_lists.append([labels.get(c, c) for c in ordered_codes])

    rows = []
    for combo, val in zip(product(*label_lists), values):
        if val is None:
            continue
        row = dict(zip(dim_ids, combo))
        row["value"] = val
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Normalise column names: lowercase, strip spaces.
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def fetch_table(table_id: str) -> pd.DataFrame:
    """Download an INE table and return it in long format."""
    url = f"{config.INE_BASE_URL}/{table_id}"
    log.info("Fetching INE table %s", table_id)
    payload = http_get_json(url)
    df = _jsonstat_to_long(payload)
    log.info("  → %d rows", len(df))
    return df


# ---------------------------------------------------------------------------
# Period parsing — INE mixes annual ("2024"), quarterly ("2024T2") and
# monthly ("2024M03") strings.  Normalise to a pandas timestamp.
# ---------------------------------------------------------------------------


def _parse_period(period: str) -> pd.Timestamp | None:
    s = str(period).strip()
    try:
        if "T" in s:  # quarterly, e.g. "2024T2"
            year, q = s.split("T")
            month = (int(q) - 1) * 3 + 1
            return pd.Timestamp(year=int(year), month=month, day=1)
        if "M" in s:  # monthly, e.g. "2024M03"
            year, m = s.split("M")
            return pd.Timestamp(year=int(year), month=int(m), day=1)
        # annual
        return pd.Timestamp(year=int(s), month=1, day=1)
    except (ValueError, TypeError):
        return None


def _find_period_column(df: pd.DataFrame) -> str | None:
    """INE labels the time dimension differently per table (Periodo, periodo…)."""
    for c in df.columns:
        if c.lower() in {"periodo", "periodos", "tiempo", "time", "ano", "año"}:
            return c
    return None


def _find_region_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        cl = c.lower()
        if "comunidad" in cl or "ccaa" in cl or cl == "regiones":
            return c
    return None


# ---------------------------------------------------------------------------
# Public extractors — one per dataset
# ---------------------------------------------------------------------------


def _standardise(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
    """Common cleanup: add `date`, `region`, rename value column."""
    if df.empty:
        return df

    period_col = _find_period_column(df)
    region_col = _find_region_column(df)

    out = df.copy()
    if period_col:
        out["date"] = out[period_col].map(_parse_period)
    if region_col:
        out = out.rename(columns={region_col: "region"})

    out = out.rename(columns={"value": value_name})

    keep = ["date", "region", value_name] + [
        c for c in out.columns
        if c not in {"date", "region", value_name, period_col}
    ]
    keep = [c for c in keep if c in out.columns]
    out = out[keep]
    out = out.dropna(subset=["date"]) if "date" in out.columns else out
    return out.sort_values("date") if "date" in out.columns else out


def fetch_house_price_index() -> pd.DataFrame:
    """Quarterly House Price Index (IPV), 2015 = 100, by Comunidad Autónoma."""
    df = fetch_table(config.INE_TABLE_HOUSE_PRICE_INDEX)
    return _standardise(df, value_name="hpi")


def fetch_rental_price_index() -> pd.DataFrame:
    """Annual Rental Price Index (IPVA), by Comunidad Autónoma."""
    df = fetch_table(config.INE_TABLE_RENTAL_PRICE_INDEX)
    return _standardise(df, value_name="rpi")


def fetch_cpi() -> pd.DataFrame:
    """Monthly Consumer Price Index (IPC), 2021 = 100, by Comunidad Autónoma."""
    df = fetch_table(config.INE_TABLE_CPI)
    return _standardise(df, value_name="cpi")


def fetch_wages() -> pd.DataFrame:
    """Annual mean gross wage by Comunidad Autónoma (€/year)."""
    df = fetch_table(config.INE_TABLE_WAGES)
    return _standardise(df, value_name="wage_eur")
