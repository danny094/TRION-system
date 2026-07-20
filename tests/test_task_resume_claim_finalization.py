from adapters.task_resume_serialization import plan_from_dict, snapshot_from_dict
from adapters.task_resume_store import (
    claim_waiting_task, finalize_claimed_failure, finalize_claimed_task,
    get_task_record, register_waiting_task,
)
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.test_task_resume_store import _NoOverrideSettings, _plan, _waiting_snapshot


def _configure(monkeypatch, tmp_path):
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))


def test_claim_owner_finalizes_result_and_active_plan_atomically(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    claimed = claim_waiting_task(task_id)
    replanned = ThinkingPlan(
        "new", [PlanStep("s2", "Step 2", "Goal 2", tool="workspace_get")],
        True, RiskLevel.SAFE, plan_id="new-plan",
    )
    snapshot = TaskLoopSnapshot(
        "new-plan", "conv-store", "Run workflow", TaskLoopState.COMPLETED, 1, 5, 1,
        completed_steps=["s2"],
    )
    result = TaskLoopResult(TaskLoopState.COMPLETED, None, [], "done", snapshot, active_plan=replanned)
    updated = finalize_claimed_task(task_id, result, expected_updated_at=claimed["updated_at"])
    assert updated["status"] == TaskLoopState.COMPLETED.value
    restored_plan = plan_from_dict(updated["plan"])
    restored_snapshot = snapshot_from_dict(updated["snapshot"])
    assert restored_plan.plan_id == "new-plan"
    assert [step.step_id for step in restored_plan.steps] == ["s2"]
    assert restored_snapshot.plan_id == "new-plan"
    assert restored_snapshot.completed_steps == ["s2"]
    assert finalize_claimed_task(task_id, result, expected_updated_at=claimed["updated_at"]) is None


def test_stale_claim_owner_cannot_overwrite_executing_record(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    claimed = claim_waiting_task(task_id)
    snapshot = TaskLoopSnapshot("plan-store", "conv-store", "Run", TaskLoopState.BLOCKED, 0, 5, 1)
    result = TaskLoopResult(TaskLoopState.BLOCKED, None, [], "blocked", snapshot)
    assert finalize_claimed_task(task_id, result, expected_updated_at="stale") is None
    assert get_task_record(task_id)["updated_at"] == claimed["updated_at"]
    assert get_task_record(task_id)["status"] == TaskLoopState.EXECUTING.value


def test_stale_claim_owner_cannot_apply_minimal_failure(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    claimed = claim_waiting_task(task_id)

    assert finalize_claimed_failure(task_id, expected_updated_at="stale") is None
    stored = get_task_record(task_id)
    assert stored["updated_at"] == claimed["updated_at"]
    assert stored["status"] == TaskLoopState.EXECUTING.value


def test_atomic_store_replace_failure_preserves_claimed_record(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    claimed = claim_waiting_task(task_id)
    snapshot = TaskLoopSnapshot("plan-store", "conv-store", "Run", TaskLoopState.BLOCKED, 0, 5, 1)
    result = TaskLoopResult(TaskLoopState.BLOCKED, None, [], "blocked", snapshot)
    monkeypatch.setattr("pathlib.Path.replace", lambda *_args: (_ for _ in ()).throw(OSError("disk")))

    with pytest.raises(OSError):
        finalize_claimed_task(task_id, result, expected_updated_at=claimed["updated_at"])

    stored = get_task_record(task_id)
    assert stored["updated_at"] == claimed["updated_at"]
    assert stored["status"] == TaskLoopState.EXECUTING.value
    assert list(tmp_path.glob(".*.tmp")) == []
import pytest
