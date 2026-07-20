import asyncio
import importlib.util
import sys
from pathlib import Path

from adapters.task_resume_serialization import plan_from_dict, plan_to_dict, snapshot_to_dict
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool
from tests.operation_contract_context import canonical_contract_context


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_tasks_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_tasks_routes_plan_criteria",
        ADMIN_API_DIR / "tasks_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _tool_detail() -> dict:
    return canonical_raw_tool(
        "container_inspect", "container_runtime", "inspect", evidence=["runtime_status"],
        required=[], scopes=["runtime_state"],
    )


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect",
        steps=[
            PlanStep(
                step_id="s1",
                title="Inspect",
                goal="Inspect runtime",
                tool="container_inspect",
                done_when="artifact_type:runtime_status",
                required_evidence=["runtime_status"],
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-criteria",
    )


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-criteria",
        conversation_id="conv-criteria",
        objective="Inspect runtime",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=0,
    )


def test_plan_roundtrip_preserves_done_when_and_required_evidence():
    parsed = plan_from_dict(plan_to_dict(_plan()))
    step = parsed.steps[0]

    assert step.done_when == "artifact_type:runtime_status"
    assert step.required_evidence == ["runtime_status"]


def test_plan_from_dict_legacy_step_uses_completion_defaults():
    parsed = plan_from_dict(
        {
            "intent": "legacy",
            "steps": [{"step_id": "s1", "title": "Legacy", "goal": "Goal"}],
            "needs_task_loop": True,
            "risk_level": "safe",
        }
    )
    step = parsed.steps[0]

    assert step.done_when == ""
    assert step.required_evidence == []


def test_approve_passes_plan_with_preserved_completion_criteria(monkeypatch):
    tasks_routes = _load_tasks_routes()
    snapshot = _snapshot()
    contract_context = canonical_contract_context(
        primary_operation="inspect", allowed_operations=("inspect",), allowed_transitions=(),
        required_evidence=("runtime_status",),
    )
    fingerprint = contract_context["routing_frame"]["operation_contract_fingerprint"]
    record = {
        "task_id": "task-criteria",
        "status": "waiting",
        "plan": plan_to_dict(_plan()),
        "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": {
            "orchestrator": {
                "available_tool_details": [_tool_detail()],
                "context": {"routing_frame": contract_context["routing_frame"]},
            },
        },
        "operation_contract_fingerprint": fingerprint,
    }
    seen = {}

    def fake_continue_task_loop(_snapshot, _user_text, plan, **kwargs):
        seen["plan"] = plan
        seen["fingerprint"] = kwargs.get("operation_contract_fingerprint")
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=[],
            visible_content="done",
            snapshot=snapshot,
        )

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda _task_id: record)
    monkeypatch.setattr(tasks_routes, "claim_waiting_task", lambda _task_id, **_kwargs: record)
    monkeypatch.setattr(tasks_routes, "get_available_tools", lambda: [_tool_detail()])
    monkeypatch.setattr(tasks_routes, "continue_task_loop", fake_continue_task_loop)
    monkeypatch.setattr(tasks_routes, "finalize_claimed_task", lambda _task_id, _result, **_kwargs: {})

    asyncio.run(tasks_routes.approve_task("task-criteria", tasks_routes.TaskApproveRequest()))

    step = seen["plan"].steps[0]
    assert step.done_when == "artifact_type:runtime_status"
    assert step.required_evidence == ["runtime_status"]
    assert seen["fingerprint"] == fingerprint
