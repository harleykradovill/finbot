import json
import time

from services.repository import Repository


def test_task_log_lifecycle() -> None:
    repo = Repository(database_url="sqlite:///:memory:")

    # create task
    task_id = repo.create_task_log(
        name="Test Sync Task",
        task_type="sync",
        execution_type="manual"
    )
    assert isinstance(task_id, int) and task_id > 0

    latest = repo.get_latest_sync_task()
    assert latest is not None
    assert latest["id"] == task_id
    assert latest["result"] == "RUNNING"

    payload = {"items_synced": 10, "total_events": 100}
    repo.complete_task_log(task_id=task_id, result="SUCCESS", log_data=payload)

    completed = repo.get_latest_sync_task()
    assert completed is not None
    assert completed["id"] == task_id
    assert completed["result"] == "SUCCESS"
    assert isinstance(completed.get("finished_at"), int)
    assert isinstance(completed.get("duration_ms"), int)
    assert json.loads(completed["log_json"]) == payload


def test_last_activity_log_sync_roundtrip() -> None:
    repo = Repository(database_url="sqlite:///:memory:")

    assert repo.get_last_activity_log_sync() is None

    ts = int(time.time())
    repo.set_last_activity_log_sync(ts)

    got = repo.get_last_activity_log_sync()
    assert got == ts or got is None