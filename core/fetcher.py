"""
HackerOne API client.

Uses the official HackerOne v1 REST API with HTTP Basic Auth
(username + API token). Fetches structured scope entries for a given
program handle.

Docs: https://api.hackerone.com/
"""

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("h1watcher.fetcher")

H1_API_BASE = "https://api.hackerone.com/v1"

# Retry on transient server errors and rate-limit responses
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_DEFAULT_TIMEOUT = 30  # seconds


def _build_session(username: str, api_token: str) -> requests.Session:
    """Build a requests Session with auth, retries, and sensible defaults."""
    session = requests.Session()
    session.auth = (username, api_token)
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "h1-scope-watcher/1.0 (github.com/yourhandle/h1-scope-watcher)",
        }
    )

    retry = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=_RETRY_STATUS_CODES,
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def _paginate(session: requests.Session, url: str) -> list[dict]:
    """
    Follow HackerOne cursor-based pagination and collect all items.
    HackerOne returns `{"data": [...], "links": {"next": "..."|null}}`.
    """
    items: list[dict] = []
    current_url: str | None = url

    while current_url:
        logger.debug("GET %s", current_url)
        resp = session.get(current_url, timeout=_DEFAULT_TIMEOUT)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            logger.warning("Rate limited — sleeping %d seconds", retry_after)
            time.sleep(retry_after)
            continue

        resp.raise_for_status()
        payload: dict = resp.json()
        items.extend(payload.get("data", []))
        current_url = (payload.get("links") or {}).get("next")

    return items


class HackerOneClient:
    """Thin wrapper around the HackerOne v1 API."""

    def __init__(self, username: str, api_token: str) -> None:
        if not username or not api_token:
            raise ValueError(
                "HackerOne username and api_token are required. "
                "Set them in config.yaml or via H1_USERNAME / H1_API_TOKEN env vars."
            )
        self._session = _build_session(username, api_token)

    def get_structured_scopes(self, handle: str) -> list[dict[str, Any]]:
        """
        Return all structured scope entries for the given program handle.

        Each entry is a dict containing at minimum:
            asset_type, asset_identifier, eligible_for_bounty,
            eligible_for_submission, instruction, max_severity
        """
        url = f"{H1_API_BASE}/hackers/programs/{handle}/structured_scopes"
        logger.info("Fetching scopes for program: %s", handle)
        raw_items = _paginate(self._session, url)

        scopes: list[dict[str, Any]] = []
        for item in raw_items:
            attrs: dict = item.get("attributes", {})
            scopes.append(
                {
                    "id": item.get("id"),
                    "asset_type": attrs.get("asset_type"),
                    "asset_identifier": attrs.get("asset_identifier"),
                    "eligible_for_bounty": attrs.get("eligible_for_bounty"),
                    "eligible_for_submission": attrs.get("eligible_for_submission"),
                    "instruction": attrs.get("instruction"),
                    "max_severity": attrs.get("max_severity"),
                    "created_at": attrs.get("created_at"),
                    "updated_at": attrs.get("updated_at"),
                }
            )

        logger.info("Fetched %d scope entries for %s", len(scopes), handle)
        return scopes

    def get_program_info(self, handle: str) -> dict[str, Any]:
        """Return basic program metadata (name, handle, offers_bounties…)."""
        url = f"{H1_API_BASE}/hackers/programs/{handle}"
        logger.debug("GET %s", url)
        resp = self._session.get(url, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        attrs = payload.get("data", {}).get("attributes", {})
        return {
            "handle": handle,
            "name": attrs.get("name", handle),
            "offers_bounties": attrs.get("offers_bounties", False),
            "state": attrs.get("state"),
            "url": f"https://hackerone.com/{handle}",
        }
