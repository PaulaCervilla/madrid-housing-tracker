"""Fallback loader: serve cached/seed CSVs when the live INE API is unreachable.

CI environments and ad-hoc runs may not always be able to reach
`servicios.ine.es` (network policy, intermittent 5xx, schema changes…).
To keep the dashboard reproducible we ship a small snapshot of the four
series under `data/seed/`.  The pipeline asks this module for any series
whose live extraction returned empty or raised.
"""
from __future__ import annotations

import logging

import pandas as pd

import config

log = logging.getLogger(__name__)

SEED_DIR = config.DATA_DIR / "seed"

_FILES = {
    "hpi":   "madrid_house_price_index.csv",
    "rpi":   "madrid_rental_price_index.csv",
    "wages": "madrid_wages.csv",
    "cpi":   "madrid_cpi.csv",
}


def load_seed(name: str) -> pd.DataFrame:
    """Load a seed CSV by short name (`hpi`, `rpi`, `wages`, `cpi`)."""
    path = SEED_DIR / _FILES[name]
    if not path.exists():
        log.warning("Seed file missing: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    log.info("Loaded seed %s (%d rows) from %s", name, len(df), path.name)
    return df
