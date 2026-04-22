"""HTTP helper with retry logic, used by all extractors."""
from __future__ import annotations

import logging
import time

import requests

import config

log = logging.getLogger(__name__)


def http_get_json(url: str, params: dict | None = None) -> dict | list:
    """GET a URL and return parsed JSON, with exponential-backoff retries."""
    headers = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    last_error: Exception | None = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            wait = 2 ** (attempt - 1)
            log.warning(
                "Request failed (attempt %d/%d) for %s: %s — retrying in %ds",
                attempt,
                config.MAX_RETRIES,
                url,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError(
        f"Failed to GET {url} after {config.MAX_RETRIES} attempts: {last_error}"
    )
