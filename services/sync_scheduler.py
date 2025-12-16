"""
Background scheduler that runs periodic sync operations.
"""

from __future__ import annotations
import threading

class SyncScheduler:
    """
    Background thread that runs sync operations on an interval.
    
    Behavior:
    - Every interval: run a lightweight full sync (users/libraries/items).
    - Only run incremental activity-log sync if a last-activity marker exists.
    """

    def __init__(self, sync_service, interval_seconds: int = 1800):
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
        import traceback

        log = logging.getLogger(__name__)
        log.debug("SyncScheduler loop starting (interval=%s)", self.interval_seconds)

        while self._running:
            try:
                self.sync_service.sync_periodic()
            except Exception:
                log.exception("Periodic sync failed")
                traceback.print_exc()

            total = float(self.interval_seconds or 0)
            slept = 0.0
            while self._running and slept < total:
                to_sleep = min(1.0, total - slept)
                time.sleep(to_sleep)
                slept += to_sleep