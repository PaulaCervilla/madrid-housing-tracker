"""End-to-end pipeline: extract → transform → load → visualize."""
from __future__ import annotations

import logging

import config
from src.extractors import ine
from src.loaders import storage
from src.transformers import affordability, cleaner
from src.visualizations import dashboard


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def run() -> None:
    configure_logging()
    log = logging.getLogger("pipeline")

    log.info("=== Step 1/4: Extracting raw data from INE ===")
    hpi_raw   = ine.fetch_house_price_index()
    rpi_raw   = ine.fetch_rental_price_index()
    cpi_raw   = ine.fetch_cpi()
    wages_raw = ine.fetch_wages()

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
