"""Discord webhook notifier."""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.differ import ScopeDiff
from notifiers.base import BaseNotifier

logger = logging.getLogger("h1watcher.notifiers.discord")

_DISCORD_COLOR_GREEN = 0x2ECC71
_DISCORD_COLOR_RED = 0xE74C3C
_DISCORD_COLOR_BLUE = 0x3498DB


def _build_session() -> requests.Session:
    """Build a requests Session with retries for the Discord webhook."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class DiscordNotifier(BaseNotifier):
    """Sends rich embed messages to a Discord channel via webhook."""

    name = "discord"

    def __init__(self, cfg: dict) -> None:
        self._webhook_url: str = cfg.get("webhook_url", "").strip()
        self._username: str = cfg.get("username", "H1 Scope Watcher")
        self._avatar_url: str = cfg.get(
            "avatar_url",
            "https://www.hackerone.com/sites/default/files/2022-01/hackerone-logo.png",
        )
        self._session = _build_session()

    def is_configured(self) -> bool:
        return bool(self._webhook_url)

    def send(self, diff: ScopeDiff, program_info: dict[str, Any]) -> None:
        lines = self.build_message_lines(diff, program_info)
        content = "\n".join(lines)

        # Choose embed colour based on what changed
        if diff.added and not diff.removed:
            color = _DISCORD_COLOR_GREEN
        elif diff.removed and not diff.added:
            color = _DISCORD_COLOR_RED
        else:
            color = _DISCORD_COLOR_BLUE

        payload = {
            "username": self._username,
            "avatar_url": self._avatar_url,
            "embeds": [
                {
                    "title": f"Scope change — {program_info.get('name', diff.handle)}",
                    "url": program_info.get("url", f"https://hackerone.com/{diff.handle}"),
                    "description": content,
                    "color": color,
                    "footer": {"text": "H1 Scope Watcher"},
                }
            ],
        }

        try:
            resp = self._session.post(self._webhook_url, json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Discord notification sent for %s", diff.handle)
        except requests.RequestException as exc:
            logger.error("Discord notification failed: %s", exc)
            raise

    def send_health(self, message: str | None = None) -> None:
        """Send a simple health / startup message to the configured webhook."""
        if not self.is_configured():
            logger.debug("Discord webhook not configured; skipping health ping")
            return

        content = message or "H1 Scope Watcher is live and healthy. Monitoring configured programs."
        payload = {
            "username": self._username,
            "avatar_url": self._avatar_url,
            "embeds": [
                {
                    "title": "H1 Scope Watcher — Healthy",
                    "description": content,
                    "color": _DISCORD_COLOR_GREEN,
                    "footer": {"text": "H1 Scope Watcher"},
                }
            ],
        }

        try:
            resp = self._session.post(self._webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("Discord health ping sent")
        except requests.RequestException as exc:
            logger.warning("Discord health ping failed: %s", exc)
