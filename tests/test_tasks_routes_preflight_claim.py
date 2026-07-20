import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from adapters import task_resume_store as store
from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool
from tests.operation_contract_context import canonical_contract_context


ROOT = Path(__file__).resolve().parents[1]


def _routes():
    admin = ROOT / "adapters" / "admin-api"
    if str(admin) not in sys.path:
        sys.path.insert(0, str(admin))
    spec = importlib.util.spec_from_file_location("z8n_tasks_routes", admin / "tasks_routes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _register(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "get_autonomy_task_resume_store_path", lambda: str(tmp_path / "tasks.json"))
    monkeypatch.setattr(store, "get_autonomy_task_resume_max_tasks", lambda: 20)
    context = canonical_contract_context(
        primary_operation="inspect", allowed_operations=("inspect",), allowed_transitions=(),
    )
    plan = ThinkingPlan(
        intent="inspect", steps=[PlanStep("step", "Inspect", "Inspect", tool="container_inspect")],
        needs_task_loop=True, risk_level=RiskLevel.NEEDS_CONFIRMATION, plan_id="plan",
    )
    snapshot = TaskLoopSnapshot(
        "plan", "conversation", "inspect", TaskLoopState.WAITING, 0, 2, 0,
        pending_step="step", stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    task_id = store.register_waiting_task(plan, snapshot, orchestrator_context=context)
    return task_id, snapshot


def _raw_tool():
    return canonical_raw_tool(
        "container_inspect", "container_runtime", "inspect", evidence=["container_metadata"],
        required=[], scopes=["runtime_state"],
    )


def _mutate_record(tmp_path, task_id, mutate):
    path = tmp_path / "tasks.json"
    payload = json.loads(path.read_text())
    mutate(payload["tasks"][task_id])
    path.write_text(json.dumps(payload))


def test_discovery_failure_keeps_real_store_waiting_and_cancelable(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_available_tools", lambda: (_ for _ in ()).throw(RuntimeError("UPSTREAM_SENTINEL")))
    monkeypatch.setattr(routes, "continue_task_loop", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not run")))

    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    assert response.status_code == 409
    assert "SENTINEL" not in response.body.decode()
    assert store.get_task_record(task_id)["status"] == TaskLoopState.WAITING.value
    cancelled = asyncio.run(routes.cancel_task(task_id))
    assert cancelled["state"] == TaskLoopState.CANCELLED.value


def test_failed_preflight_can_retry_then_claim_once(monkeypatch, tmp_path):
    routes = _routes()
    task_id, snapshot = _register(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [])
    first = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))
    assert first.status_code == 409
    assert store.get_task_record(task_id)["status"] == TaskLoopState.WAITING.value

    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(routes, "make_tool_runner", lambda: lambda _call: None)
    completed = snapshot.transition_to(TaskLoopState.EXECUTING, pending_step="", stop_reason=None)
    completed = completed.transition_to(TaskLoopState.REFLECTING)
    completed = completed.transition_to(TaskLoopState.COMPLETED, current_step_index=1)
    monkeypatch.setattr(
        routes, "continue_task_loop",
        lambda *_args, **_kwargs: TaskLoopResult(TaskLoopState.COMPLETED, None, [], "done", completed),
    )

    second = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))
    assert second["state"] == TaskLoopState.COMPLETED.value
    assert store.get_task_record(task_id)["status"] == TaskLoopState.COMPLETED.value


def test_corrupt_contract_preflight_never_claims_real_waiting_record(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    _mutate_record(
        tmp_path, task_id,
        lambda record: record["orchestrator_context"]["routing_frame"]["operation_contract"].__setitem__(
            "allowed_operations", "inspect",
        ),
    )
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(routes, "continue_task_loop", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not run")))

    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    assert response.status_code == 409
    assert store.get_task_record(task_id)["status"] == TaskLoopState.WAITING.value


def test_fingerprint_only_preflight_never_claims_real_waiting_record(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    _mutate_record(
        tmp_path, task_id,
        lambda record: record["orchestrator_context"]["routing_frame"].pop("operation_contract"),
    )
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])

    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))

    assert response.status_code == 409
    assert store.get_task_record(task_id)["status"] == TaskLoopState.WAITING.value


def test_post_claim_exception_is_cas_finalized_blocked_without_detail_leak(monkeypatch, tmp_path):
    routes = _routes()
    task_id, _snapshot = _register(monkeypatch, tmp_path)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_raw_tool()])
    monkeypatch.setattr(routes, "make_tool_runner", lambda: lambda _call: None)
    monkeypatch.setattr(
        routes, "continue_task_loop",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("POST_CLAIM_SECRET_SENTINEL")),
    )

    response = asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))
    stored = store.get_task_record(task_id)

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "error_code": "internal_error", "message": "Ein interner Fehler ist aufgetreten.",
    }
    assert "SENTINEL" not in response.body.decode()
    assert stored["status"] == TaskLoopState.BLOCKED.value
    assert stored["snapshot"]["state"] == TaskLoopState.BLOCKED.value
    assert stored["snapshot"]["stop_reason"] == StopReason.STEP_FAILED.value
    with pytest.raises(HTTPException) as approve_error:
        asyncio.run(routes.approve_task(task_id, routes.TaskApproveRequest()))
    with pytest.raises(HTTPException) as cancel_error:
        asyncio.run(routes.cancel_task(task_id))
    assert approve_error.value.detail == "task_not_waiting"
    assert cancel_error.value.detail == "task_not_waiting"
