"""
Notifier dispatcher — discovers which notifiers are configured and fires them all.

Only notifiers that have their required credentials set will be used.
If none are configured, a warning is logged but execution continues normally.
"""

import logging
from typing import Any

from core.differ import ScopeDiff
from notifiers.base import BaseNotifier
from notifiers.discord import DiscordNotifier
from notifiers.telegram import TelegramNotifier
from notifiers.slack import SlackNotifier

logger = logging.getLogger("h1watcher.notifiers.dispatcher")

# Registry of all supported notifiers
_NOTIFIER_CLASSES: list[type[BaseNotifier]] = [
    DiscordNotifier,
    TelegramNotifier,
    SlackNotifier,
]


class NotifierDispatcher:
    """
    Instantiates every supported notifier and keeps only those that are
    properly configured. Dispatches diffs to all active notifiers.
    """

    def __init__(self, notifiers_cfg: dict[str, Any]) -> None:
        self._active: list[BaseNotifier] = []

        for cls in _NOTIFIER_CLASSES:
            notifier_name = cls.name
            cfg = notifiers_cfg.get(notifier_name, {})
            instance = cls(cfg)
            if instance.is_configured():
                self._active.append(instance)
                logger.info("Notifier enabled: %s", notifier_name)
            else:
                logger.debug("Notifier not configured, skipping: %s", notifier_name)

        if not self._active:
            logger.warning(
                "No notifiers are configured! "
                "Set up at least one (discord / telegram / slack) in config.yaml "
                "or via environment variables."
            )

    @property
    def active_names(self) -> list[str]:
        return [n.name for n in self._active]

    def send(self, diff: ScopeDiff, program_info: dict[str, Any]) -> None:
        """
        Send the scope diff notification to every active notifier.
        Errors in one notifier do not prevent others from firing.
        """
        if not self._active:
            logger.warning("No active notifiers — change will not be dispatched.")
            return

        for notifier in self._active:
            try:
                notifier.send(diff, program_info)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Notifier '%s' raised an error: %s", notifier.name, exc, exc_info=True
                )

    def send_health(self, message: str) -> None:
        """Send a health/startup message to all notifiers that support it."""
        if not self._active:
            logger.warning("No active notifiers available for health ping.")
            return

        for notifier in self._active:
            send_health_fn = getattr(notifier, "send_health", None)
            if callable(send_health_fn):
                try:
                    send_health_fn(message)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Health ping failed for notifier '%s': %s", notifier.name, exc, exc_info=True
                    )
            else:
                logger.debug("Notifier '%s' does not implement send_health(), skipping", notifier.name)
