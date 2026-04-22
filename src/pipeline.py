"""End-to-end pipeline: extract → transform → load → visualize."""
from __future__ import annotations

import logging
import os
from typing import Callable

import pandas as pd

import config
from src.extractors import ine, seed
from src.loaders import storage
from src.transformers import affordability, cleaner
from src.visualizations import dashboard


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _safe_fetch(name: str, fetcher: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    """Try the live extractor; on failure or empty result, use bundled seed.

    Set the env var ``USE_SEED_DATA=1`` to skip the network entirely.
    """
    log = logging.getLogger("pipeline")
    if os.environ.get("USE_SEED_DATA") == "1":
        log.info("USE_SEED_DATA=1 — skipping live fetch for %s", name)
        return seed.load_seed(name)
    try:
        df = fetcher()
        if df is None or df.empty:
            log.warning("Live fetch for %s returned empty — using seed.", name)
            return seed.load_seed(name)
        return df
    except Exception as exc:  # noqa: BLE001 — fallback path is the point
        log.warning("Live fetch for %s failed (%s) — using seed.", name, exc)
        return seed.load_seed(name)


def run() -> None:
    configure_logging()
    log = logging.getLogger("pipeline")

    log.info("=== Step 1/4: Extracting raw data from INE (with seed fallback) ===")
    hpi_raw   = _safe_fetch("hpi",   ine.fetch_house_price_index)
    rpi_raw   = _safe_fetch("rpi",   ine.fetch_rental_price_index)
    cpi_raw   = _safe_fetch("cpi",   ine.fetch_cpi)
    wages_raw = _safe_fetch("wages", ine.fetch_wages)

    log.info("=== Step 2/4: Transforming ===")
    hpi   = cleaner.keep_general_index(cleaner.filter_region(hpi_raw,   config.TARGET_REGION))
    rpi   = cleaner.keep_general_index(cleaner.filter_region(rpi_raw,   config.TARGET_REGION))
    cpi   = cleaner.keep_general_index(cleaner.filter_region(cpi_raw,   config.TARGET_REGION))
    wages = cleaner.filter_region(wages_raw, config.TARGET_REGION)

    aff = affordability.build_affordability_table(hpi, rpi, wages, cpi)

    log.info("=== Step 3/4: Loading ===")
    storage.save_csv(hpi,   "madrid_house_price_index")
    storage.save_csv(rpi,   "madrid_rental_price_index")
    storage.save_csv(cpi,   "madrid_cpi")
    storage.save_csv(wages, "madrid_wages")
    storage.save_csv(aff,   "madrid_affordability")
    storage.save_sqlite({
        "house_price_index":  hpi,
        "rental_price_index": rpi,
        "cpi":                cpi,
        "wages":              wages,
        "affordability":      aff,
    })

    log.info("=== Step 4/4: Building dashboard ===")
    out = dashboard.build_dashboard(aff)
    log.info("Done. Open %s in a browser.", out)


if __name__ == "__main__":
    run()
