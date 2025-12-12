import time
import threading

from services.sync_scheduler import SyncScheduler

class SyncResultStub:
    def __init__(self, success: bool = True):
        self.success = success

class FakeSyncService:
    def sync_full(self):
        time.sleep(0.01)
        return SyncResultStub(success=True)

def test_sync_scheduler_start_stop_lifecycle() -> None:
    svc = FakeSyncService()
    sched = SyncScheduler(sync_service=svc, interval_seconds=1)

    sched.start()
    time.sleep(0.2)

    assert getattr(sched, "_running", False) is True
    thread = getattr(sched, "_thread", None)
    assert thread is not None and isinstance(thread, threading.Thread)
    assert thread.is_alive()

    sched.stop()
    time.sleep(0.1)
    assert getattr(sched, "_running", False) is False
    thread_after = getattr(sched, "_thread", None)
    assert thread_after is None or not thread_after.is_alive()


def test_sync_scheduler_start_idempotent() -> None:
    svc = FakeSyncService()
    sched = SyncScheduler(sync_service=svc, interval_seconds=1)

    sched.start()
    time.sleep(0.15)
    first_thread = getattr(sched, "_thread", None)

    sched.start()
    time.sleep(0.15)
    second_thread = getattr(sched, "_thread", None)

    assert first_thread is second_thread

    sched.stop()
    time.sleep(0.1)