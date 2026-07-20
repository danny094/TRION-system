"""P11 SP3-F Fund C: approve_task() muss tool_truth_source intern sichtbar
machen (Auditierbarkeit fuer Observer/Resume), darf den JSON-Response-Body
aber NICHT um ein neues Feld erweitern (Doc19/Doc38 WebUI-Vertrag bleibt
unveraendert). Eigene Datei statt Erweiterung von test_tasks_routes.py,
um den Doc07-200-Zeilen-Cap nicht zu verletzen.
"""
import asyncio
import importlib.util
import sys
from pathlib import Path

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
        "trion_tasks_routes_for_tests_tool_truth_source",
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
        plan_id="plan-route-tts",
    )


def _waiting_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-route-tts",
        conversation_id="conv-route-tts",
        objective="Resume me",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        max_replans=2,
        pending_step="s1",
    )


def _workspace_tool_detail() -> dict:
    return canonical_raw_tool(
        "workspace_get", "workspace", "read", evidence=["workspace_state"],
        required=[], scopes=["workspace_state"], output_schema="mcp_output_schema",
    )


def _fake_continue(snapshot, user_text, passed_plan, *, tool_runner, replanner_fn):
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
        completed_steps=["s1"],
        pending_step="",
        artifacts=[{"id": "a1"}],
    )
    return TaskLoopResult(
        state=TaskLoopState.COMPLETED,
        stop_reason=None,
        artifacts=[{"id": "a1"}],
        visible_content="done",
        snapshot=finished,
    )


def test_tasks_approve_route_logs_tool_truth_source_without_changing_response_body(monkeypatch):
    tasks_routes = _load_tasks_routes()
    stored = {
        "task_id": "task-456",
        "status": "waiting",
        "plan": plan_to_dict(_plan()),
        "snapshot": snapshot_to_dict(_waiting_snapshot()),
        "orchestrator_context": {},
    }
    logged = []

    monkeypatch.setattr(tasks_routes, "get_task_record", lambda task_id: stored if task_id == "task-456" else None)
    monkeypatch.setattr(tasks_routes, "claim_waiting_task", lambda task_id, **_kwargs: stored if task_id == "task-456" else None)
    monkeypatch.setattr(tasks_routes, "get_available_tools", lambda: [_workspace_tool_detail()])
    monkeypatch.setattr(tasks_routes, "make_tool_runner", lambda: (lambda call: None))
    monkeypatch.setattr(tasks_routes, "log_debug", lambda msg: logged.append(msg))
    monkeypatch.setattr(tasks_routes, "continue_task_loop", _fake_continue)
    monkeypatch.setattr(tasks_routes, "finalize_claimed_task", lambda task_id, result, **_kwargs: {"ok": True})

    response = asyncio.run(
        tasks_routes.approve_task(
            "task-456",
            tasks_routes.TaskApproveRequest(user_text="freigeben"),
        )
    )

    assert any("live_registry_mirror" in msg for msg in logged)
    assert "tool_truth_source" not in response, (
        "Resume/Approve-Response-Body darf um kein neues Feld erweitert werden "
        "(Doc19/Doc38 WebUI-Vertrag)."
    )
