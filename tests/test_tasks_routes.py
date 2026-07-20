import asyncio
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import HTTPException

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.canonical_tool_raw import canonical_raw_tool


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_tasks_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_tasks_routes_for_tests",
        ADMIN_API_DIR / "tasks_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Step 1", goal="Goal 1", tool="workspace_get")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-route",
    )


def _waiting_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-route",
        conversation_id="conv-route",
        objective="Resume me",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        max_replans=2,
        pending_step="s1",
    )


def _tool_detail() -> dict:
    return canonical_raw_tool(
        "workspace_get", "workspace", "inspect", evidence=["workspace_entry"],
        required=[], scopes=["workspace_state"],
    )


def test_tasks_approve_route_continues_waiting_task(monkeypatch):
    tasks_routes = _load_tasks_routes()
    plan = replace(_plan(), plan_id="PLAN_ID_SENTINEL")
    waiting = replace(
        _waiting_snapshot(), plan_id="PLAN_ID_SENTINEL",
        conversation_id="CONVERSATION_ID_SENTINEL", objective="USER_TEXT_SENTINEL",
        pending_step="STEP_ID_SENTINEL", waiting_reason="WAITING_REASON_SENTINEL",
        waiting_source="WAITING_SOURCE_SENTINEL",
    )
    stored = {
        "task_id": "TASK_ID_SENTINEL",
        "status": "waiting",
        "plan": plan_to_dict(plan),
        "snapshot": snapshot_to_dict(waiting),
        "orchestrator_context": {},
    }
    seen = {}

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: stored if task_id == "TASK_ID_SENTINEL" else None)
    monkeypatch.setattr(tasks_routes, "claim_waiting_task", lambda task_id, **_kwargs: stored if task_id == "TASK_ID_SENTINEL" else None)
    monkeypatch.setattr(tasks_routes, "get_available_tools", lambda: [_tool_detail()])
    monkeypatch.setattr(tasks_routes, "make_tool_runner", lambda: (lambda call: None))
    private_artifact = {
        "artifact_type": "SECRET_SENTINEL", "id": "STEP_ID_SENTINEL",
        "target": "TARGET_SENTINEL", "scope": "SCOPE_SENTINEL",
        "tool_name": "TOOL_NAME_SENTINEL", "arguments": "ARGUMENT_SENTINEL",
        "content": "ARTIFACT_CONTENT_SENTINEL", "output": "OUTPUT_SENTINEL",
        "operation_contract_fingerprint": "FP_SENTINEL",
    }

    def fake_continue(snapshot, user_text, passed_plan, *, tool_runner, replanner_fn):
        seen["snapshot"] = snapshot
        seen["user_text"] = user_text
        seen["plan"] = passed_plan
        seen["replanner_fn"] = replanner_fn
        finished = TaskLoopSnapshot(
            plan_id=snapshot.plan_id,
            conversation_id=snapshot.conversation_id,
            objective=snapshot.objective,
            state=TaskLoopState.COMPLETED,
            current_step_index=1,
            max_steps=snapshot.max_steps,
            max_retries_per_step=snapshot.max_retries_per_step,
            replan_count=snapshot.replan_count,
            max_replans=snapshot.max_replans,
            completed_steps=["STEP_ID_SENTINEL"], pending_step="STEP_ID_SENTINEL",
            waiting_reason="WAITING_REASON_SENTINEL", waiting_source="WAITING_SOURCE_SENTINEL",
            artifacts=[private_artifact],
        )
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=[private_artifact],
            visible_content="done",
            snapshot=finished,
        )

    saved = {}

    def fake_save(task_id, result, **_kwargs):
        saved["task_id"] = task_id
        saved["state"] = result.state
        return {"ok": True}

    monkeypatch.setattr(tasks_routes, "continue_task_loop", fake_continue)
    monkeypatch.setattr(tasks_routes, "finalize_claimed_task", fake_save)

    response = asyncio.run(
        tasks_routes.approve_task(
            "TASK_ID_SENTINEL",
            tasks_routes.TaskApproveRequest(user_text="USER_INPUT_SENTINEL"),
        )
    )

    assert "task_id" not in response
    assert response["state"] == "completed"
    assert response["visible_content"] == "done"
    assert "completed_steps" not in response["snapshot"]
    assert response["artifacts"] == [{"artifact_type": "artifact"}]
    assert "SENTINEL" not in json.dumps(response)
    assert response["snapshot"]["state"] == "completed"
    assert response["snapshot"]["current_step_index"] == 1
    assert seen["user_text"] == "USER_INPUT_SENTINEL"
    assert seen["plan"].plan_id == "PLAN_ID_SENTINEL"
    assert seen["snapshot"].state == TaskLoopState.WAITING
    assert callable(seen["replanner_fn"])
    assert saved == {"task_id": "TASK_ID_SENTINEL", "state": TaskLoopState.COMPLETED}


def test_tasks_approve_route_rejects_non_waiting_task(monkeypatch):
    tasks_routes = _load_tasks_routes()
    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: {"status": "executing"})

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            tasks_routes.approve_task(
                "task-closed",
                tasks_routes.TaskApproveRequest(),
            )
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "task_not_waiting"
    assert "task-closed" not in repr(exc.value.detail)


def test_tasks_approve_route_returns_404_for_missing_task(monkeypatch):
    tasks_routes = _load_tasks_routes()
    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            tasks_routes.approve_task(
                "task-missing",
                tasks_routes.TaskApproveRequest(),
            )
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "task_not_found"
