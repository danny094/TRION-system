import asyncio
import importlib.util
import sys
from pathlib import Path

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict
from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool
from tests.operation_contract_context import canonical_contract_context

ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_tasks_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_tasks_routes_resume_executable_now",
        ADMIN_API_DIR / "tasks_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _tool_detail() -> dict:
    return canonical_raw_tool(
        "container_inspect", "container_runtime", "inspect", evidence=["container_metadata"],
        required=["container_id_or_name"], scopes=["runtime_state"],
    )


def test_resume_approve_blocks_missing_required_args_before_tool_runner(monkeypatch):
    tasks_routes = _load_tasks_routes()
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
        failure_escalation="abort",
        pending_step="s1",
        stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    contract_context = canonical_contract_context(
        primary_operation="inspect", allowed_operations=("inspect",), allowed_transitions=(),
    )
    record = {
        "task_id": "task-required-args",
        "status": "waiting",
        "plan": plan_to_dict(plan),
        "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": {
            "orchestrator": {
                "context": {
                    "routing_frame": contract_context["routing_frame"],
                },
            },
        },
        "operation_contract_fingerprint": contract_context["routing_frame"]["operation_contract_fingerprint"],
    }
    called = {"tool_runner": False}

    def tool_runner(_call):
        called["tool_runner"] = True
        raise AssertionError("tool_runner must not be called")

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: record)
    monkeypatch.setattr(tasks_routes, "claim_waiting_task", lambda task_id, **_kwargs: record)
    monkeypatch.setattr(
        tasks_routes,
        "get_available_tools",
        lambda: [_tool_detail()],
    )
    monkeypatch.setattr(tasks_routes, "make_tool_runner", lambda: tool_runner)
    monkeypatch.setattr(tasks_routes, "finalize_claimed_task", lambda task_id, result, **_kwargs: {"ok": True})

    response = asyncio.run(
        tasks_routes.approve_task(
            "task-required-args",
            tasks_routes.TaskApproveRequest(user_text="approve"),
        )
    )

    assert called["tool_runner"] is False
    assert response["state"] == TaskLoopState.BLOCKED.value
    assert response["snapshot"]["error_count"] == 1
