import json
from services.data_models import TaskLog


def test_tasklog_to_dict_with_json_log() -> None:
    payload = {"items_synced": 5, "total_events": 50}
    raw = json.dumps(payload)
    t = TaskLog(
        name="initial-sync",
        type="sync",
        execution_type="manual",
        started_at=1000,
        finished_at=1500,
        duration_ms=500,
        result="RUNNING",
        log_json=raw,
    )

    d = t.to_dict()
    assert "log" in d
    assert isinstance(d["log"], dict)
    assert d["log"] == payload


def test_tasklog_to_dict_with_invalid_log_string() -> None:
    raw = "not-a-json-string"
    t = TaskLog(
        name="initial-sync",
        type="sync",
        execution_type="manual",
        started_at=2000,
        finished_at=None,
        duration_ms=0,
        result="FAILED",
        log_json=raw,
    )

    d = t.to_dict()
    assert "log" in d
    assert d["log"] == raw


def test_tasklog_to_dict_with_none_log() -> None:
    t = TaskLog(
        name="initial-sync",
        type="sync",
        execution_type="manual",
        started_at=3000,
        finished_at=None,
        duration_ms=0,
        result="PENDING",
        log_json=None,
    )

    d = t.to_dict()
    assert "log" in d
    assert d["log"] is None