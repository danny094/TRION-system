import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from adapters.task_resume_store import (
    cancel_waiting_task,
    claim_waiting_task,
    get_task_record,
    register_waiting_task,
)
from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


class _NoOverrideSettings:
    def get(self, key, default=None):
        return default


def test_cancel_waiting_task_marks_cancelled_and_blocks_claim(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())

    record = cancel_waiting_task(task_id)

    assert isinstance(record, dict)
    assert record["status"] == TaskLoopState.CANCELLED.value
    assert record["snapshot"]["state"] == TaskLoopState.CANCELLED.value
    assert record["snapshot"]["stop_reason"] == StopReason.USER_CANCELLED.value
    with pytest.raises(ValueError, match=f"task_not_waiting:{task_id}"):
        claim_waiting_task(task_id)


def test_cancel_waiting_task_returns_none_for_unknown(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)

    assert cancel_waiting_task("task-missing") is None


def test_cancel_waiting_task_rejects_claimed_task(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    claim_waiting_task(task_id)

    with pytest.raises(ValueError, match=f"task_not_waiting:{task_id}"):
        cancel_waiting_task(task_id)


def test_cancel_route_cancels_waiting_task(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    tasks_routes = _load_tasks_routes()

    response = asyncio.run(tasks_routes.cancel_task(task_id))

    assert response == {
        "state": TaskLoopState.CANCELLED.value,
        "stop_reason": StopReason.USER_CANCELLED.value,
    }
    assert task_id not in repr(response)
    assert get_task_record(task_id)["status"] == TaskLoopState.CANCELLED.value


def test_approve_after_cancel_does_not_continue(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    cancel_waiting_task(task_id)
    tasks_routes = _load_tasks_routes()
    monkeypatch.setattr(
        tasks_routes,
        "continue_task_loop",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not continue")),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(tasks_routes.approve_task(task_id, tasks_routes.TaskApproveRequest()))

    assert exc.value.status_code == 409
    assert str(exc.value.detail) == "task_not_waiting"
    assert task_id not in str(exc.value.detail)


def test_cancel_route_returns_404_for_unknown_task(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)
    tasks_routes = _load_tasks_routes()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(tasks_routes.cancel_task("task-missing"))

    assert exc.value.status_code == 404


def test_cancel_route_returns_409_for_non_waiting_task(monkeypatch, tmp_path):
    _use_store(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    claim_waiting_task(task_id)
    tasks_routes = _load_tasks_routes()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(tasks_routes.cancel_task(task_id))

    assert exc.value.status_code == 409
    assert str(exc.value.detail) == "task_not_waiting"
    assert task_id not in str(exc.value.detail)


def _use_store(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))


def _load_tasks_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_tasks_routes_cancel_tests",
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
        plan_id="plan-cancel",
    )


def _waiting_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-cancel",
        conversation_id="conv-cancel",
        objective="Cancel me",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        max_replans=2,
        pending_step="s1",
    )
