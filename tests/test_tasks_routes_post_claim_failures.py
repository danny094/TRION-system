import asyncio
import json

import pytest

from adapters import task_resume_store as store
from adapters import task_resume_finalization as finalization
from core.task_loop.contracts import StopReason, TaskLoopState
from core.task_loop.executor import TaskToolResult
from tests.test_tasks_routes_preflight_claim import _raw_tool, _register, _routes


def _assert_generic_blocked(response, task_id):
    stored = store.get_task_record(task_id)
    assert response.status_code == 500
    assert json.loads(response.body) == {
        "error_code": "internal_error", "message": "Ein interner Fehler ist aufgetreten.",
    }
    assert stored["status"] == TaskLoopState.BLOCKED.value
    assert stored["snapshot"]["stop_reason"] == StopReason.STEP_FAILED.value


def test_real_replanner_exception_after_claim_finalizes_blocked(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    path = tmp_path / "tasks.json"
    payload = json.loads(path.read_text())
    payload["tasks"][task_id]["snapshot"]["max_replans"] = 1
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(
        routes, "make_tool_runner",
        lambda: lambda _call: TaskToolResult(False, {}, "TOOL_FAILURE_SENTINEL"),
    )
    monkeypatch.setattr(
        routes, "build_replan",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("REPLANNER_SECRET_SENTINEL")),
    )
    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))
    _assert_generic_blocked(response, task_id)
    assert "SENTINEL" not in response.body.decode()


def test_real_task_loop_executor_exception_after_claim_finalizes_blocked(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(routes, "make_tool_runner", lambda: lambda _call: TaskToolResult(True, {}))
    monkeypatch.setattr(
        "core.task_loop.runner.execute_step",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("EXECUTOR_SECRET_SENTINEL")),
    )
    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))
    _assert_generic_blocked(response, task_id)
    assert "SENTINEL" not in response.body.decode()


@pytest.mark.parametrize("failure_point", ["snapshot", "plan", "apply"])
def test_result_preparation_or_apply_exception_uses_minimal_cas_failure(monkeypatch, tmp_path, failure_point):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(routes, "make_tool_runner", lambda: lambda _call: TaskToolResult(True, {}))
    if failure_point == "snapshot":
        monkeypatch.setattr(finalization, "snapshot_to_dict", _raise_finalization)
    elif failure_point == "plan":
        monkeypatch.setattr(finalization, "plan_to_dict", _raise_finalization)
    else:
        monkeypatch.setattr(store, "_apply_result", _raise_finalization)

    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    _assert_generic_blocked(response, task_id)
    assert "FINALIZATION_SECRET_SENTINEL" not in response.body.decode()


def test_persistent_write_failure_does_not_claim_a_durable_blocked_state(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(routes, "make_tool_runner", lambda: lambda _call: TaskToolResult(True, {}))
    real_save = store._save_store
    calls = {"count": 0}

    def fail_after_claim(payload):
        calls["count"] += 1
        if calls["count"] == 1:
            return real_save(payload)
        raise OSError("STORE_SECRET_SENTINEL")

    monkeypatch.setattr(store, "_save_store", fail_after_claim)
    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    assert response.status_code == 500
    assert "SENTINEL" not in response.body.decode()
    assert store.get_task_record(task_id)["status"] == TaskLoopState.EXECUTING.value
    assert calls["count"] == 3


def _raise_finalization(*_args, **_kwargs):
    raise RuntimeError("FINALIZATION_SECRET_SENTINEL")
