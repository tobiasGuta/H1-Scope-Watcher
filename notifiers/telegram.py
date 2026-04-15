"""Telegram Bot API notifier."""

import logging
from typing import Any

import requests

from core.differ import ScopeDiff
from notifiers.base import BaseNotifier

logger = logging.getLogger("h1watcher.notifiers.telegram")

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier(BaseNotifier):
    """
    Sends Markdown messages via Telegram Bot API.

    Requirements:
        1. Create a bot with @BotFather → get the token.
        2. Start a conversation with your bot (or add it to a group).
        3. Get your chat_id via https://api.telegram.org/bot<TOKEN>/getUpdates
    """

    name = "telegram"

    def __init__(self, cfg: dict) -> None:
        self._token: str = cfg.get("bot_token", "").strip()
        self._chat_id: str = str(cfg.get("chat_id", "")).strip()

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, diff: ScopeDiff, program_info: dict[str, Any]) -> None:
        lines = self.build_message_lines(diff, program_info)
        text = "\n".join(lines)

        # Telegram Markdown has a 4096-char limit per message
        chunks = _split_message(text, max_len=4000)

        url = _TELEGRAM_API.format(token=self._token)

        for chunk in chunks:
            payload = {
                "chat_id": self._chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            try:
                resp = requests.post(url, json=payload, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as exc:
                logger.error("Telegram notification failed: %s", exc)
                raise

        logger.info("Telegram notification sent for %s", diff.handle)


def _split_message(text: str, max_len: int = 4000) -> list[str]:
    """Split a long message into chunks that fit within Telegram's limit."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in text.splitlines():
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_len and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
