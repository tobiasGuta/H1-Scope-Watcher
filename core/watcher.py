"""
Watcher — orchestrates fetch → diff → notify → save for every program.
"""

import logging
import time
from typing import Any

from core.fetcher import HackerOneClient
from core.storage import SnapshotStorage
from core.differ import diff_scopes, ScopeDiff
from notifiers.dispatcher import NotifierDispatcher

logger = logging.getLogger("h1watcher.watcher")


class ScopeWatcher:
    """
    Central controller that ties together the fetcher, storage, differ,
    and notification dispatcher.
    """

    def __init__(self, cfg: dict[str, Any], log: logging.Logger) -> None:
        self._cfg = cfg
        self._log = log

        h1_cfg = cfg.get("hackerone", {})
        self._client = HackerOneClient(
            username=h1_cfg.get("username", ""),
            api_token=h1_cfg.get("api_token", ""),
        )

        storage_cfg = cfg.get("storage", {})
        self._storage = SnapshotStorage(
            storage_path=storage_cfg.get("path", "snapshots")
        )

        self._dispatcher = NotifierDispatcher(cfg.get("notifiers", {}))

        programs_raw: list = cfg.get("programs", [])
        self._programs: list[dict] = self._normalise_programs(programs_raw)
        if not self._programs:
            raise ValueError(
                "No programs configured. Add at least one entry under 'programs:' in config.yaml."
            )

        logger.info(
            "Watching %d program(s): %s",
            len(self._programs),
            ", ".join(p["handle"] for p in self._programs),
        )

    def send_health(self) -> None:
        """Send a startup/health message to configured notifiers.

        This is a convenience wrapper that constructs a short message and
        asks the notifier dispatcher to send it where supported.
        """
        try:
            num_programs = len(self._programs)
            notifiers = ", ".join(self._dispatcher.active_names) or "none configured"
            message = (
                f"H1 Scope Watcher is live and healthy. Continuously watching {num_programs} program(s). "
                f"Notifiers: {notifiers}."
            )
            self._dispatcher.send_health(message)
        except Exception:
            logger.exception("Failed to send health ping to notifiers")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_check(self) -> None:
        """Perform one full check across all configured programs."""
        logger.info("Starting scope check…")
        for program in self._programs:
            handle = program["handle"]
            try:
                self._check_program(handle)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error checking program %s: %s", handle, exc, exc_info=True)
        logger.info("Scope check complete.")

    def run_scheduled(self) -> None:
        """Run checks in an infinite loop according to the configured interval."""
        interval_minutes: int = (
            self._cfg.get("scheduler", {}).get("interval_minutes", 30)
        )
        logger.info("Scheduler active — checking every %d minute(s)", interval_minutes)

        while True:
            self.run_check()
            sleep_seconds = interval_minutes * 60
            logger.info("Sleeping %d minutes until next check…", interval_minutes)
            time.sleep(sleep_seconds)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_program(self, handle: str) -> None:
        logger.info("Checking program: %s", handle)

        new_scopes = self._client.get_structured_scopes(handle)
        old_scopes = self._storage.load(handle)

        if old_scopes is None:
            # First run — save baseline, no notification (nothing to diff against)
            logger.info(
                "First run for %s — saving baseline (%d entries). "
                "You will be notified on the next change.",
                handle,
                len(new_scopes),
            )
            self._storage.save(handle, new_scopes)
            return

        diff: ScopeDiff = diff_scopes(handle, old_scopes, new_scopes)

        if diff.has_changes:
            logger.info("Changes detected for %s: %s", handle, diff.summary)
            try:
                program_info = self._client.get_program_info(handle)
            except Exception:  # noqa: BLE001
                program_info = {"handle": handle, "name": handle, "url": f"https://hackerone.com/{handle}"}

            self._dispatcher.send(diff, program_info)
            self._storage.save(handle, new_scopes)
        else:
            logger.info("No changes for %s", handle)

    @staticmethod
    def _normalise_programs(programs_raw: list) -> list[dict]:
        """Accept programs as strings or dicts."""
        result = []
        for p in programs_raw:
            if isinstance(p, str):
                result.append({"handle": p})
            elif isinstance(p, dict) and "handle" in p:
                result.append(p)
            else:
                logger.warning("Skipping invalid program entry: %r", p)
        return result
