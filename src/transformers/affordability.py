"""Affordability calculator.

Given the cleaned series for Madrid, derive:

* `price_per_m2`  — €/m² implied by the IPV index, anchored at 2015.
* `rent_per_m2`   — €/m²/month implied by the IPVA index.
* `purchase_price`— absolute purchase price for a typical dwelling.
* `annual_rent`   — annual rent for that dwelling.
* `price_to_income` — price / gross annual wage  (classic affordability ratio).
* `rent_burden`   — annual rent / gross annual wage  (% of income spent on rent).
* `years_to_save` — years needed to save the down-payment, given a savings
                    rate over net income (after IRPF & SS).

Everything is returned as a single tidy DataFrame indexed by year.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

import config

log = logging.getLogger(__name__)


def _anchor_index_to_absolute(
    series: pd.Series, anchor_year: int, anchor_value: float
) -> pd.Series:
    """Convert an index series into absolute units using a known anchor point."""
    if anchor_year not in series.index:
        # Fall back to the closest year available.
        anchor_year = min(series.index, key=lambda y: abs(y - anchor_year))
    base = series.loc[anchor_year]
    if base == 0 or pd.isna(base):
        return pd.Series(dtype=float)
    return series * (anchor_value / base)


def build_affordability_table(
    hpi: pd.DataFrame,
    rpi: pd.DataFrame,
    wages: pd.DataFrame,
    cpi: pd.DataFrame,
    *,
    dwelling_size_m2: float = config.DEFAULT_DWELLING_SIZE_M2,
    savings_rate: float = config.DEFAULT_SAVINGS_RATE,
    down_payment_ratio: float = config.DEFAULT_DOWN_PAYMENT_RATIO,
) -> pd.DataFrame:
    """Combine all four series into a single annual table for Madrid."""

    def _annual(df: pd.DataFrame, col: str) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float, name=col)
        s = df.copy()
        s["year"] = pd.to_datetime(s["date"]).dt.year
        return s.groupby("year")[col].mean()

    s_hpi   = _annual(hpi, "hpi")
    s_rpi   = _annual(rpi, "rpi")
    s_wage  = _annual(wages, "wage_eur")
    s_cpi   = _annual(cpi, "cpi")

    if s_hpi.empty:
        log.warning("HPI series is empty — cannot build affordability table.")
        return pd.DataFrame()

    # Anchor indices to known €/m² values at their respective base years.
    price_per_m2 = _anchor_index_to_absolute(
        s_hpi, anchor_year=2015, anchor_value=config.ANCHOR_PRICE_PER_M2_2015
    )
    rent_per_m2 = _anchor_index_to_absolute(
        s_rpi, anchor_year=2015, anchor_value=config.DEFAULT_RENT_PER_M2_2015
    ) if not s_rpi.empty else pd.Series(dtype=float)

    df = pd.DataFrame({
        "hpi": s_hpi,
        "rpi": s_rpi,
        "cpi": s_cpi,
        "wage_eur": s_wage,
        "price_per_m2": price_per_m2,
        "rent_per_m2_month": rent_per_m2,
    })
    df.index.name = "year"

    # Forward-fill wages (annual survey published with lag) so latest years
    # still have an estimate.
    df["wage_eur"] = df["wage_eur"].ffill()

    df["purchase_price"] = df["price_per_m2"] * dwelling_size_m2
    df["annual_rent"]    = df["rent_per_m2_month"] * dwelling_size_m2 * 12

    # Classic price-to-income ratio (gross).
    df["price_to_income"] = df["purchase_price"] / df["wage_eur"]
    df["rent_burden"]     = df["annual_rent"]    / df["wage_eur"]

    # Years to save the down-payment, given a savings rate over net income.
    net_income = df["wage_eur"] * config.NET_TO_GROSS_RATIO
    annual_savings = net_income * savings_rate
    down_payment = df["purchase_price"] * down_payment_ratio
    df["years_to_down_payment"] = down_payment / annual_savings

    # And years to fully buy outright (cash) — a more striking figure.
    df["years_to_full_purchase"] = df["purchase_price"] / annual_savings

    df = df.replace([np.inf, -np.inf], np.nan).reset_index()
    return df
