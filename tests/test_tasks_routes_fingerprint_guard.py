import asyncio
import importlib.util
import json
import sys
from pathlib import Path

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict
from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool

ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_tasks_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_tasks_routes_fingerprint_guard",
        ADMIN_API_DIR / "tasks_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _tool_detail() -> dict:
    return canonical_raw_tool(
        "container_inspect", "container_runtime", "inspect", evidence=["container_metadata"],
        required=[], scopes=["runtime_state"],
    )


def _record(*, stored_fingerprint=None, include_stored=True) -> dict:
    plan = ThinkingPlan(
        intent="inspect",
        steps=[PlanStep(step_id="s1", title="Inspect", goal="Inspect", tool="container_inspect")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="resume-plan",
    )
    snapshot = TaskLoopSnapshot(
        plan_id="resume-plan",
        conversation_id="conv",
        objective="Inspect container",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=0,
        pending_step="s1",
        stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    record = {
        "task_id": "task-fingerprint",
        "status": "waiting",
        "plan": plan_to_dict(plan),
        "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": {
            "orchestrator": {
                "available_tool_details": [_tool_detail()],
                "context": {
                    "routing_frame": {"operation_contract_fingerprint": "routing-fp"},
                },
            },
        },
    }
    if include_stored:
        record["operation_contract_fingerprint"] = stored_fingerprint
    return record


def test_approve_blocks_fingerprint_mismatch_before_continue(monkeypatch):
    tasks_routes = _load_tasks_routes()
    called = {"continue": False}

    def continue_task_loop(*_args, **_kwargs):
        called["continue"] = True
        raise AssertionError("continue_task_loop must not be called")

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: _record(stored_fingerprint="stored-fp"))
    monkeypatch.setattr(tasks_routes, "get_available_tools", lambda: [_tool_detail()])
    monkeypatch.setattr(tasks_routes, "continue_task_loop", continue_task_loop)

    response = asyncio.run(tasks_routes.approve_task("task-fingerprint", tasks_routes.TaskApproveRequest()))
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "error_code": "plan_contract_rejected",
        "message": "Der Plan konnte nicht freigegeben werden.",
    }
    assert called["continue"] is False


def test_approve_old_record_without_stored_fingerprint_fails_closed_not_crash(monkeypatch):
    tasks_routes = _load_tasks_routes()
    called = {"continue": False}

    def continue_task_loop(*_args, **_kwargs):
        called["continue"] = True
        raise AssertionError("continue_task_loop must not be called")

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: _record(include_stored=False))
    monkeypatch.setattr(tasks_routes, "get_available_tools", lambda: [_tool_detail()])
    monkeypatch.setattr(tasks_routes, "continue_task_loop", continue_task_loop)

    response = asyncio.run(tasks_routes.approve_task("task-fingerprint", tasks_routes.TaskApproveRequest()))
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "error_code": "plan_contract_rejected",
        "message": "Der Plan konnte nicht freigegeben werden.",
    }
    assert called["continue"] is False
