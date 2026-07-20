import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict
from core.pipeline.plan_contract_validator import PlanContractDecision
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API = ROOT / "adapters" / "admin-api"


def _tasks_routes():
    if str(ADMIN_API) not in sys.path:
        sys.path.insert(0, str(ADMIN_API))
    spec = importlib.util.spec_from_file_location("p11_public_tasks_routes", ADMIN_API / "tasks_routes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _record() -> dict:
    plan = ThinkingPlan(
        intent="run", steps=[PlanStep(step_id="STEP_SENTINEL", title="Step", goal="Run")],
        needs_task_loop=True, risk_level=RiskLevel.SAFE, plan_id="PLAN_SENTINEL",
    )
    snapshot = TaskLoopSnapshot(
        plan_id="PLAN_SENTINEL", conversation_id="CONVERSATION_SENTINEL",
        objective="TARGET_SENTINEL", state=TaskLoopState.WAITING,
        current_step_index=0, max_steps=2, max_retries_per_step=0,
    )
    return {
        "status": TaskLoopState.WAITING.value,
        "plan": plan_to_dict(plan), "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": {},
    }


@pytest.mark.parametrize("reason", [
    "plan_contract_unknown_tool:TOOL_SENTINEL:SECRET_SENTINEL",
    "plan_contract_missing_tool_metadata:TOOL_SENTINEL:METADATA_SENTINEL",
    "plan_contract_fingerprint_mismatch:FP_SENTINEL:SCOPE_SENTINEL",
    "plan_contract_missing_fingerprint:TARGET_SENTINEL:TASK_SENTINEL",
])
def test_approve_plan_contract_rejection_is_fixed_and_non_leaking(monkeypatch, reason):
    routes = _tasks_routes()
    monkeypatch.setattr(routes, "get_task_record", lambda _task_id: _record())
    monkeypatch.setattr(routes, "claim_waiting_task", lambda _task_id, **_kwargs: _record())
    monkeypatch.setattr(routes, "get_available_tools", lambda: [])
    monkeypatch.setattr(
        routes, "validate_plan_contract",
        lambda *_a, **_k: PlanContractDecision(allowed=False, reason=reason),
    )

    response = asyncio.run(routes.approve_task("TASK_SENTINEL", routes.TaskApproveRequest()))
    body = json.loads(response.body)
    serialized = json.dumps(body)
    assert response.status_code == 409
    assert body == {
        "error_code": "plan_contract_rejected",
        "message": "Der Plan konnte nicht freigegeben werden.",
    }
    assert "SENTINEL" not in serialized
    assert reason not in serialized
