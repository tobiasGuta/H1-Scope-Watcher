"""Base class that all notifier implementations must extend."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from core.differ import ScopeDiff

logger = logging.getLogger("h1watcher.notifiers")


class BaseNotifier(ABC):
    """Abstract notifier. Subclasses implement `send()`."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when this notifier has the required credentials."""

    @abstractmethod
    def send(self, diff: ScopeDiff, program_info: dict[str, Any]) -> None:
        """
        Dispatch a notification for the given scope diff.

        Args:
            diff:         The computed diff object.
            program_info: Basic program metadata dict (name, handle, url, …).
        """

    # ------------------------------------------------------------------
    # Shared formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_emoji(severity: str | None) -> str:
        mapping = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "none": "⚪",
        }
        return mapping.get((severity or "").lower(), "⚪")

    @staticmethod
    def _bounty_label(eligible: bool | None) -> str:
        if eligible is True:
            return "💰 Bounty"
        if eligible is False:
            return "🚫 No bounty"
        return "❓ Unknown"

    @classmethod
    def _format_scope_entry(cls, scope: dict) -> str:
        identifier = scope.get("asset_identifier", "N/A")
        asset_type = scope.get("asset_type", "N/A")
        bounty = cls._bounty_label(scope.get("eligible_for_bounty"))
        severity = scope.get("max_severity")
        sev_emoji = cls._severity_emoji(severity)
        sev_label = severity.capitalize() if severity else "N/A"
        return f"`{identifier}` [{asset_type}] — {bounty} | {sev_emoji} {sev_label}"

    @classmethod
    def build_message_lines(
        cls, diff: ScopeDiff, program_info: dict[str, Any]
    ) -> list[str]:
        """Build a human-readable list of message lines (no platform decoration)."""
        name = program_info.get("name", diff.handle)
        url = program_info.get("url", f"https://hackerone.com/{diff.handle}")
        lines: list[str] = [
            f"🔍 *{name}* scope changed!",
            f"🔗 {url}",
            f"📊 Summary: {diff.summary}",
            "",
        ]

        if diff.added:
            lines.append(f"✅ *Added* ({len(diff.added)})")
            for s in diff.added:
                lines.append(f"  • {cls._format_scope_entry(s)}")
            lines.append("")

        if diff.removed:
            lines.append(f"❌ *Removed* ({len(diff.removed)})")
            for s in diff.removed:
                lines.append(f"  • {cls._format_scope_entry(s)}")
            lines.append("")

        if diff.modified:
            lines.append(f"✏️ *Modified* ({len(diff.modified)})")
            for change in diff.modified:
                old_s = change["old"]
                new_s = change["new"]
                identifier = new_s.get("asset_identifier", "N/A")
                lines.append(f"  • `{identifier}`")
                # Show what changed
                for field in ("eligible_for_bounty", "eligible_for_submission", "max_severity", "instruction"):
                    old_val = old_s.get(field)
                    new_val = new_s.get(field)
                    if old_val != new_val:
                        lines.append(f"    ↳ {field}: {old_val!r} → {new_val!r}")
            lines.append("")

        return lines
