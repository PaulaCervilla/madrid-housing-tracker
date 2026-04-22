"""Configuration: API endpoints, dataset codes, and constants.

All datasets used in this project come from public Spanish statistics:
- INE (Instituto Nacional de Estadística) JSON-stat API:  https://www.ine.es/dyngs/DataLab/manual.html?cid=64
- Banco de España / public OECD-style aggregates as fallbacks.

Datasets:
* IPV  — Índice de Precios de Vivienda (purchase price index, base 2015=100)
* IPVA — Índice de Precios de Alquiler de Vivienda (rental price index)
* EPA  — Encuesta de Población Activa, salario medio anual
* IPC  — Índice de Precios de Consumo (cost of living, base 2021=100)
"""
from __future__ import annotations

from pathlib import Path

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
DB_PATH = DATA_DIR / "madrid_housing.db"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# --- INE JSON-stat API ---
# Generic endpoint:  https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table_id}
INE_BASE_URL = "https://servicios.ine.es/wstempus/jsstat/ES/DATOS_TABLA"

# House Price Index (IPV) — quarterly, by Comunidad Autónoma + national.
# Table 25171: General index, new + second-hand dwellings.
INE_TABLE_HOUSE_PRICE_INDEX = "25171"

# Rental Price Index (IPVA) — annual, by Comunidad Autónoma + national.
# Table 59061: General index of rental prices for housing.
INE_TABLE_RENTAL_PRICE_INDEX = "59061"

# Consumer Price Index (IPC) — monthly, base 2021 = 100, national + CCAA.
# Table 50902: general IPC by Comunidad Autónoma.
INE_TABLE_CPI = "50902"

# Average annual gross wage by Comunidad Autónoma — Encuesta Anual de Estructura Salarial.
# Table 28192: salary mean, total workers.
INE_TABLE_WAGES = "28192"

# Region of interest in this project. INE codes regions by name in JSON-stat,
# so we keep both the human-readable label and a slug.
TARGET_REGION = "Madrid, Comunidad de"
TARGET_REGION_SLUG = "madrid"
NATIONAL_LABEL = "Nacional"
NATIONAL_ALIASES = {"Nacional", "Total Nacional", "España"}

# --- Affordability assumptions ---
# Average dwelling size used to convert the price index into an absolute
# purchase price.  We anchor the index series to a known average price for
# Madrid in the base year (€/m²), sourced from public Ministry of Transport
# statistics (Mitma, 2015 average for Comunidad de Madrid: ~2,400 €/m²).
ANCHOR_PRICE_PER_M2_2015 = 2400.0      # €/m² in 2015 (IPV base year)
DEFAULT_DWELLING_SIZE_M2 = 80.0        # typical 2-3 bedroom flat
DEFAULT_RENT_PER_M2_2015 = 11.0        # €/m²/month, Madrid 2015 baseline

# Affordability calculator defaults
DEFAULT_SAVINGS_RATE = 0.20            # 20% of net income saved per year
DEFAULT_DOWN_PAYMENT_RATIO = 0.20      # banks typically require 20%
NET_TO_GROSS_RATIO = 0.78              # ~22% withheld between IRPF + SS

# --- HTTP ---
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
USER_AGENT = (
    "madrid-housing-tracker/1.0 "
    "(+https://github.com/example/madrid-housing-tracker)"
)
