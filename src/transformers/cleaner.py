"""Cleaning + filtering helpers for INE data."""
from __future__ import annotations

import logging

import pandas as pd

import config

log = logging.getLogger(__name__)


def filter_region(df: pd.DataFrame, region_label: str) -> pd.DataFrame:
    """Keep only rows for a given Comunidad Autónoma label.

    INE uses both "Madrid, Comunidad de" and "Comunidad de Madrid" depending
    on the table.  We accept any region whose name contains "Madrid".
    """
    if df.empty or "region" not in df.columns:
        return df
    needle = region_label.split(",")[0].strip().lower()  # "madrid"
    mask = df["region"].astype(str).str.lower().str.contains(needle)
    return df[mask].copy()


def filter_national(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "region" not in df.columns:
        return df
    mask = df["region"].astype(str).isin(config.NATIONAL_ALIASES)
    return df[mask].copy()


def keep_general_index(df: pd.DataFrame) -> pd.DataFrame:
    """For IPV/IPVA/IPC tables, keep only the headline 'General' index row.

    INE breaks each index into many sub-categories (new vs. second-hand
    housing, food vs. transport, etc.).  We only need the headline number.
    """
    if df.empty:
        return df

    candidates = [c for c in df.columns
                  if c.lower() not in {"date", "region"}
                  and df[c].dtype == object]
    out = df.copy()
    for col in candidates:
        vals = out[col].astype(str).str.lower()
        general_mask = vals.str.contains("general") | vals.str.contains("índice general")
        if general_mask.any():
            out = out[general_mask]
    return out


def annual_average(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Collapse sub-annual frequencies (monthly/quarterly) to annual mean."""
    if df.empty or "date" not in df.columns:
        return df
    out = df.copy()
    out["year"] = pd.to_datetime(out["date"]).dt.year
    grouped = (
        out.groupby(["year", "region"], as_index=False)[value_col].mean()
    )
    grouped["date"] = pd.to_datetime(grouped["year"].astype(str) + "-01-01")
    return grouped[["date", "year", "region", value_col]].sort_values("date")
