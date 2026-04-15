"""
Scope differ — computes what changed between two scope snapshots.

Compares by `asset_identifier` (the target URL / app name) within each
asset_type bucket. Detects:
  • New targets added
  • Targets removed
  • Attribute changes (bounty eligibility, severity ceiling, etc.)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScopeDiff:
    """Container for the diff result between two scope snapshots."""

    handle: str
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    modified: list[dict[str, Any]] = field(default_factory=list)  # list of {"old":…, "new":…}

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)

    @property
    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        if self.modified:
            parts.append(f"~{len(self.modified)} modified")
        return ", ".join(parts) if parts else "no changes"


# Fields that are meaningful to compare for modifications.
# We intentionally exclude timestamps.
_TRACKED_FIELDS = {
    "asset_type",
    "asset_identifier",
    "eligible_for_bounty",
    "eligible_for_submission",
    "max_severity",
    "instruction",
}


def _key(scope: dict) -> str:
    """Stable identity key for a scope entry."""
    return f"{scope.get('asset_type', '')}::{scope.get('asset_identifier', '')}"


def _comparable(scope: dict) -> dict:
    return {k: scope.get(k) for k in _TRACKED_FIELDS}


def diff_scopes(
    handle: str,
    old: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> ScopeDiff:
    """
    Compute the difference between the old and new scope lists.

    Args:
        handle: Program handle (for labelling the result).
        old:    Previously saved scope entries (may be empty list on first run).
        new:    Freshly fetched scope entries.

    Returns:
        A ScopeDiff describing what changed.
    """
    result = ScopeDiff(handle=handle)

    old_map = {_key(s): s for s in old}
    new_map = {_key(s): s for s in new}

    old_keys = set(old_map)
    new_keys = set(new_map)

    # Added
    for k in new_keys - old_keys:
        result.added.append(new_map[k])

    # Removed
    for k in old_keys - new_keys:
        result.removed.append(old_map[k])

    # Modified (same identity, different tracked attributes)
    for k in old_keys & new_keys:
        if _comparable(old_map[k]) != _comparable(new_map[k]):
            result.modified.append({"old": old_map[k], "new": new_map[k]})

    return result
