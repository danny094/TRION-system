import asyncio
import json

import pytest
from fastapi import HTTPException

from adapters import task_resume_store as store
from adapters.task_resume_serialization import (
    plan_from_dict, plan_to_dict, snapshot_from_dict, snapshot_to_dict,
)
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from tests.test_tasks_routes_preflight_claim import _mutate_record, _register, _routes


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_step_index", True),
        ("current_step_index", "1"),
        ("current_step_index", 1.0),
        ("completed_steps", [7]),
        ("completed_steps", [True]),
        ("completed_steps", "STEP_ID_SENTINEL"),
        ("completed_steps", ["step", 7]),
        ("pending_step", 7),
        ("pending_step", True),
        ("step_operation_executions", None),
        ("step_operation_executions", "RECEIPT_SENTINEL"),
        ("step_operation_executions", {}),
        ("step_operation_executions", True),
        ("step_operation_executions", 7),
        ("step_operation_executions", [{"receipt": {"step_id": "incomplete"}, "status": "success"}]),
        ("previous_state", "STATE_SENTINEL"),
    ],
)
def test_malformed_persisted_snapshot_is_rejected_before_claim(monkeypatch, tmp_path, field, value):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    before = store.get_task_record(task_id)
    _mutate_record(tmp_path, task_id, lambda record: record["snapshot"].__setitem__(field, value))
    calls = []
    monkeypatch.setattr(routes, "get_available_tools", lambda: calls.append("discovery"))
    monkeypatch.setattr(routes, "make_tool_runner", lambda: calls.append("runner"))

    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    after = store.get_task_record(task_id)
    assert error.value.status_code == 409
    assert error.value.detail == "task_record_corrupt"
    assert "SENTINEL" not in json.dumps({"detail": error.value.detail})
    assert after["status"] == "waiting"
    assert after["updated_at"] == before["updated_at"]
    assert calls == []


@pytest.mark.parametrize("step_id", [7, True])
def test_malformed_persisted_step_id_is_rejected_before_claim(monkeypatch, tmp_path, step_id):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    _mutate_record(
        tmp_path, task_id,
        lambda record: record["plan"]["steps"][0].__setitem__("step_id", step_id),
    )
    monkeypatch.setattr(
        routes, "claim_waiting_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not claim")),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    assert error.value.detail == "task_record_corrupt"
    assert store.get_task_record(task_id)["status"] == "waiting"


def test_non_list_completed_steps_is_rejected_without_iterable_normalization():
    _routes_data = snapshot_to_dict(_register_snapshot())
    _routes_data["completed_steps"] = ("step",)
    with pytest.raises(ValueError):
        snapshot_from_dict(_routes_data)


def test_non_list_receipt_history_is_rejected_without_iterable_normalization():
    data = snapshot_to_dict(_register_snapshot())
    data["step_operation_executions"] = ()
    with pytest.raises(ValueError):
        snapshot_from_dict(data)


def test_missing_receipt_history_is_legacy_readable_but_active_mode_blocks(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    before = store.get_task_record(task_id)
    _mutate_record(
        tmp_path, task_id,
        lambda record: record["snapshot"].pop("step_operation_executions"),
    )
    calls = []
    monkeypatch.setattr(routes, "get_available_tools", lambda: calls.append("discovery"))
    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    after = store.get_task_record(task_id)
    legacy = snapshot_to_dict(_register_snapshot())
    legacy.pop("step_operation_executions")
    assert snapshot_from_dict(legacy).step_operation_executions == []
    assert response.status_code == 409
    assert json.loads(response.body)["error_code"] == "plan_contract_rejected"
    assert after["status"] == "waiting"
    assert after["updated_at"] == before["updated_at"]
    assert calls == []


def test_snapshot_roundtrip_preserves_typed_previous_state():
    snapshot = _register_snapshot().transition_to(TaskLoopState.CANCELLED)
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    assert restored.state is TaskLoopState.CANCELLED
    assert restored.previous_state is TaskLoopState.WAITING


@pytest.mark.parametrize("value", ["unknown", True, 7, {}])
def test_malformed_previous_state_is_rejected(value):
    data = snapshot_to_dict(_register_snapshot())
    data["previous_state"] = value
    with pytest.raises(ValueError):
        snapshot_from_dict(data)


def test_missing_legacy_previous_state_remains_none():
    data = snapshot_to_dict(_register_snapshot())
    data.pop("previous_state")
    assert snapshot_from_dict(data).previous_state is None


def test_valid_resume_plan_and_snapshot_roundtrip_remains_typed(monkeypatch, tmp_path):
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    record = store.get_task_record(task_id)
    assert plan_to_dict(plan_from_dict(record["plan"])) == record["plan"]
    assert snapshot_to_dict(snapshot_from_dict(record["snapshot"])) == record["snapshot"]


def _register_snapshot():
    return TaskLoopSnapshot("plan", "conversation", "objective", TaskLoopState.WAITING, 0, 2, 0)
