import asyncio
import importlib.util
import sys
from pathlib import Path

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict
from core.orchestrator.contracts import ToolDescriptor
from core.pipeline import task_loop_stage
from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.task_loop import continue_task_loop, start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool
from tests.operation_contract_context import canonical_contract_context


def _contract_context():
    return canonical_contract_context(
        primary_operation="inspect", allowed_operations=("inspect",), allowed_transitions=(),
    )


def _tool():
    return ToolDescriptor(
        name="container_inspect", capability_domain="container_runtime",
        capability_operation="inspect", capability_evidence_types=["container_metadata"],
        capability_target_scopes=["runtime_state"], capability_risk="read_only",
    )


def _tool_dict():
    return canonical_raw_tool(
        "container_inspect", "container_runtime", "inspect", evidence=["container_metadata"],
        required=[], scopes=["runtime_state"],
    )


def _plan(risk=RiskLevel.SAFE):
    return ThinkingPlan(
        intent="inspect", steps=[PlanStep(
            step_id="inspect-step", title="Inspect", goal="Inspect",
            tool="container_inspect", risk=risk,
        )], needs_task_loop=True, risk_level=risk, plan_id="receipt-plan",
    )


def test_initial_receipt_failure_blocks_before_tool_start(monkeypatch):
    calls = []
    monkeypatch.setattr(task_loop_stage, "issue_initial_step_receipt", lambda *_a, **_k: None)

    result = task_loop_stage.build_task_loop_stage(
        _plan(), conversation_id="conv", objective="inspect", task_loop_fn=start_task_loop,
        tool_runner=lambda call: calls.append(call) or TaskToolResult(True, {}),
        replanner_fn=None, max_steps=2, max_retries_per_step=0, max_replans=0,
        available_tools=[_tool()], orchestrator_context=_contract_context(),
    ).result

    assert result.state is TaskLoopState.BLOCKED
    assert calls == []
    assert result.snapshot.step_operation_executions == []


def test_active_receipt_mode_without_issuer_blocks_old_waiting_snapshot():
    snapshot = TaskLoopSnapshot(
        "receipt-plan", "conv", "inspect", TaskLoopState.WAITING, 0, 2, 0,
        pending_step="inspect-step", stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    calls = []

    result = continue_task_loop(
        snapshot, "approve", _plan(RiskLevel.NEEDS_CONFIRMATION),
        tool_runner=lambda call: calls.append(call) or TaskToolResult(True, {}),
        operation_contract_fingerprint="contract-fp", receipt_mode=True,
    )

    assert result.state is TaskLoopState.BLOCKED
    assert calls == []


def test_approve_route_reissues_initial_receipt_before_tool_start(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    admin = root / "adapters" / "admin-api"
    if str(admin) not in sys.path:
        sys.path.insert(0, str(admin))
    spec = importlib.util.spec_from_file_location("z8k_tasks_routes", admin / "tasks_routes.py")
    routes = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(routes)

    plan = _plan(RiskLevel.NEEDS_CONFIRMATION)
    snapshot = TaskLoopSnapshot(
        "receipt-plan", "conv", "inspect", TaskLoopState.WAITING, 0, 2, 0,
        pending_step="inspect-step", stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    context = {"orchestrator": {
        "available_tool_details": [{
            "name": "container_inspect", "capability_domain": "wrong",
            "capability_operation": "delete",
        }], "context": _contract_context(),
    }}
    record = {
        "status": "waiting", "plan": plan_to_dict(plan), "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": context,
        "operation_contract_fingerprint": _contract_context()["routing_frame"]["operation_contract_fingerprint"],
    }
    calls = []
    monkeypatch.setattr(routes, "get_task_record", lambda _task_id: record)
    monkeypatch.setattr(routes, "claim_waiting_task", lambda _task_id, **_kwargs: record)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [_tool_dict()])
    monkeypatch.setattr(
        routes, "make_tool_runner",
        lambda: lambda call: calls.append(call.tool_name) or TaskToolResult(True, {}),
    )
    monkeypatch.setattr(routes, "finalize_claimed_task", lambda *_a, **_k: {"ok": True})

    response = asyncio.run(routes.approve_task("task", routes.TaskApproveRequest()))

    assert calls == ["container_inspect"]
    assert response["state"] == TaskLoopState.COMPLETED.value


def test_approve_route_blocks_when_canonical_descriptor_truth_is_missing(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    admin = root / "adapters" / "admin-api"
    if str(admin) not in sys.path:
        sys.path.insert(0, str(admin))
    spec = importlib.util.spec_from_file_location("z8m_tasks_routes", admin / "tasks_routes.py")
    routes = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(routes)
    plan = _plan(RiskLevel.NEEDS_CONFIRMATION)
    snapshot = TaskLoopSnapshot(
        "receipt-plan", "conv", "inspect", TaskLoopState.WAITING, 0, 2, 0,
        pending_step="inspect-step", stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    record = {
        "status": "waiting", "plan": plan_to_dict(plan), "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": {"context": _contract_context()},
        "operation_contract_fingerprint": _contract_context()["routing_frame"]["operation_contract_fingerprint"],
    }
    calls = []
    monkeypatch.setattr(routes, "get_task_record", lambda _task_id: record)
    monkeypatch.setattr(routes, "claim_waiting_task", lambda _task_id, **_kwargs: record)
    monkeypatch.setattr(routes, "get_available_tools", lambda: [])
    monkeypatch.setattr(routes, "make_tool_runner", lambda: lambda call: calls.append(call))

    response = asyncio.run(routes.approve_task("task", routes.TaskApproveRequest()))

    assert response.status_code == 409
    assert calls == []
