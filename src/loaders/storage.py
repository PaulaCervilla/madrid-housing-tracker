"""Persistence helpers — save tidy DataFrames as CSV and SQLite."""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Mapping

import pandas as pd

import config

log = logging.getLogger(__name__)


def save_csv(df: pd.DataFrame, name: str) -> None:
    path = config.DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    log.info("Saved %s rows → %s", len(df), path.name)


def save_sqlite(tables: Mapping[str, pd.DataFrame]) -> None:
    with sqlite3.connect(config.DB_PATH) as con:
        for name, df in tables.items():
            df.to_sql(name, con, if_exists="replace", index=False)
            log.info("SQLite: wrote %s (%d rows)", name, len(df))
