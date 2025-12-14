"""
Background scheduler that runs periodic sync operations.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Optional

from services.sync_service import SyncService


@dataclass
class SyncScheduler:
    """
    Background thread that runs sync operations on an interval.
    
    Behavior:
    - Every interval: run a lightweight full sync (users/libraries/items).
    - Only run incremental activity-log sync if a last-activity marker exists.
    """

    def __init__(self, sync_service, interval_seconds: int = 120):
        self.sync_service = sync_service
        self.interval_seconds = int(interval_seconds)
        self._thread = None
        self._running = False

    def start(self) -> None:
        """Start the background sync thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        self._thread.start()
        print(
            f"SyncScheduler started "
            f"(interval: {self.interval_seconds}s)"
        )

    def stop(self) -> None:
        """Stop the background sync thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("SyncScheduler stopped")

    def _run_loop(self) -> None:
        import time
        import logging

        logging.basicConfig(level=logging.INFO)

        log = logging.getLogger(__name__)
        log.debug("SyncScheduler loop starting (interval=%s)", self.interval_seconds)

        # TODO (WATCHDOG):
        # - A separate watchdog worker should be implemented to poll active sessions
        #   frequently while Borealis is running. That worker will
        #   update live session durations and increment play counts on session end.
        while self._running:
            try:
                log.info("SyncScheduler: running periodic full sync (lightweight)")
                try:
                    self.sync_service.sync_full(auto_track=False)
                except Exception as exc:
                    log.exception("Periodic full sync failed: %s", exc)
            except Exception:
                log.exception("Unexpected error during periodic full sync")

            try:
                last_marker = None
                try:
                    last_marker = self.sync_service.repository.get_last_activity_log_sync()
                except Exception:
                    log.exception("Failed to read last activity log sync marker; skipping incremental")
                    last_marker = None

                if last_marker:
                    log.info(
                        "SyncScheduler: running incremental activity log sync (since marker=%s)",
                        last_marker,
                    )
                    try:
                        self.sync_service.sync_activity_log_incremental()
                    except Exception as exc:
                        log.exception("Incremental activity log sync failed: %s", exc)
                else:
                    log.info("No last_activity_log_sync marker present; skipping incremental activity log sync")
            except Exception:
                log.exception("Unexpected error during incremental sync decision")

            for _ in range(self.interval_seconds):
                if not self._running:
                    break
                time.sleep(1)