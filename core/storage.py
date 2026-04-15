"""
Storage layer — persists scope snapshots as JSON files on disk.

Each program gets its own file: <storage_path>/<handle>.json
This keeps state simple, portable, and inspectable without any database.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("h1watcher.storage")


class SnapshotStorage:
    """Read / write JSON scope snapshots keyed by program handle."""

    def __init__(self, storage_path: str = "snapshots") -> None:
        self._path = storage_path
        os.makedirs(self._path, exist_ok=True)
        logger.debug("Snapshot storage directory: %s", os.path.abspath(self._path))

    def _file(self, handle: str) -> str:
        # Sanitise handle so it's safe as a filename
        safe = handle.replace("/", "_").replace("..", "_")
        return os.path.join(self._path, f"{safe}.json")

    def load(self, handle: str) -> list[dict[str, Any]] | None:
        """
        Load the last saved scope snapshot for *handle*.

        Returns:
            List of scope dicts, or None if no snapshot exists yet.
        """
        fpath = self._file(handle)
        if not os.path.exists(fpath):
            logger.debug("No existing snapshot for %s", handle)
            return None

        try:
            with open(fpath, "r") as fh:
                data = json.load(fh)
            logger.debug("Loaded snapshot for %s (%d entries)", handle, len(data))
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read snapshot for %s: %s", handle, exc)
            return None

    def save(self, handle: str, scopes: list[dict[str, Any]]) -> None:
        """Persist the current scope list for *handle*."""
        fpath = self._file(handle)
        try:
            with open(fpath, "w") as fh:
                json.dump(scopes, fh, indent=2, default=str)
            logger.debug("Saved snapshot for %s (%d entries)", handle, len(scopes))
        except OSError as exc:
            logger.error("Failed to save snapshot for %s: %s", handle, exc)
            raise
