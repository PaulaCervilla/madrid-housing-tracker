"""HTTP helper with retry logic, used by all extractors."""
from __future__ import annotations

import logging
import time

import requests

import config

log = logging.getLogger(__name__)


def http_get_json(url: str, params: dict | None = None) -> dict | list:
    """GET a URL and return parsed JSON, with exponential-backoff retries.

    If the server replies with non-JSON content (e.g. an HTML error page),
    we log a snippet of the body so the failure is easy to diagnose.
    """
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
            try:
                return resp.json()
            except ValueError as exc:
                snippet = resp.text[:200].replace("\n", " ")
                raise ValueError(
                    f"Non-JSON response (Content-Type={resp.headers.get('content-type')!r}): "
                    f"{snippet!r}"
                ) from exc
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
