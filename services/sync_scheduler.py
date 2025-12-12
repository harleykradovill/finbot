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
    
    Handles both initial full activity log pulls and periodic
    incremental syncs for recent playback activity.
    """

    sync_service: SyncService
    interval_seconds: int = 1800  # 30 minutes

    def __post_init__(self) -> None:
        self._running = False
        self._thread: Optional[threading.Thread] = None

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
        """
        Main loop that runs sync operations periodically.
        """
        while self._running:
            try:
                # Phase 1: Full sync of users, libraries, items
                full_result = (
                    self.sync_service.sync_full()
                )
                status = (
                    "SUCCESS" if full_result.success
                    else "FAILED"
                )
                print(
                    f"Full sync {status}: "
                    f"{full_result.users_synced} users, "
                    f"{full_result.libraries_synced} libraries, "
                    f"{full_result.items_synced} items "
                    f"({full_result.duration_ms}ms)"
                )

                # Phase 2: Incremental activity log sync
                activity_result = (
                    self.sync_service
                    .sync_activity_log_incremental(
                        minutes_back=30
                    )
                )
                status = (
                    "SUCCESS" if activity_result.success
                    else "FAILED"
                )
                print(
                    f"Incremental activity log sync {status}: "
                    f"{activity_result.items_synced} events "
                    f"({activity_result.duration_ms}ms)"
                )

            except Exception as exc:
                print(f"Scheduled sync error: {exc}")

            for _ in range(self.interval_seconds):
                if not self._running:
                    break
                time.sleep(1)