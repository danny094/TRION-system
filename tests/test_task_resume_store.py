from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

from adapters.task_resume_serialization import plan_from_dict, snapshot_from_dict
from adapters.task_resume_store import claim_waiting_task, finalize_claimed_task, get_task_record, register_waiting_task


class _NoOverrideSettings:
    def get(self, key, default=None):
        return default


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Step 1", goal="Goal 1", tool="workspace_get")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-store",
    )


def _waiting_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-store",
        conversation_id="conv-store",
        objective="Run workflow",
        state=TaskLoopState.WAITING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        max_replans=2,
        pending_step="s1",
    )


def test_task_resume_store_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))

    task_id = register_waiting_task(_plan(), _waiting_snapshot(), orchestrator_context={"k": "v"}, available_tools=[{"name": "workspace_get"}])
    record = get_task_record(task_id)

    assert isinstance(record, dict)
    assert record["task_id"] == task_id
    assert record["status"] == "waiting"
    assert record["conversation_id"] == "conv-store"

    parsed_plan = plan_from_dict(record["plan"])
    parsed_snapshot = snapshot_from_dict(record["snapshot"])
    assert parsed_plan.plan_id == "plan-store"
    assert parsed_snapshot.state == TaskLoopState.WAITING
    assert parsed_snapshot.pending_step == "s1"

    completed_snapshot = TaskLoopSnapshot(
        plan_id=parsed_snapshot.plan_id,
        conversation_id=parsed_snapshot.conversation_id,
        objective=parsed_snapshot.objective,
        state=TaskLoopState.COMPLETED,
        current_step_index=1,
        max_steps=parsed_snapshot.max_steps,
        max_retries_per_step=parsed_snapshot.max_retries_per_step,
        replan_count=parsed_snapshot.replan_count,
        max_replans=parsed_snapshot.max_replans,
        completed_steps=["s1"],
        pending_step="",
        artifacts=[{"id": "a1"}],
    )
    result = TaskLoopResult(
        state=TaskLoopState.COMPLETED,
        stop_reason=None,
        artifacts=[{"id": "a1"}],
        visible_content="done",
        snapshot=completed_snapshot,
    )
    claimed = claim_waiting_task(task_id)
    updated = finalize_claimed_task(task_id, result, expected_updated_at=claimed["updated_at"])

    assert isinstance(updated, dict)
    assert updated["status"] == "completed"
    assert updated["result"]["visible_content"] == "done"
    assert updated["snapshot"]["state"] == "completed"


def test_register_waiting_task_persists_tool_truth_source(monkeypatch, tmp_path):
    """P11 SP3-F Fund C: tool_truth_source muss im Resume-Record sichtbar sein,
    damit Observer/Resume den Fallback-Fall nicht mit gefilterter Wahrheit
    verwechseln (Danny-DECIDE Option 1)."""
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))

    task_id = register_waiting_task(
        _plan(),
        _waiting_snapshot(),
        orchestrator_context={"k": "v"},
        available_tools=[{"name": "workspace_get"}],
        tool_truth_source="orchestrator_filtered",
    )
    record = get_task_record(task_id)

    assert isinstance(record, dict)
    assert record["tool_truth_source"] == "orchestrator_filtered"


def test_register_waiting_task_persists_operation_contract_fingerprint(monkeypatch, tmp_path):
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))
    context = {
        "orchestrator": {
            "context": {
                "routing_frame": {"operation_contract_fingerprint": "fp-store"},
            },
        },
    }

    task_id = register_waiting_task(
        _plan(),
        _waiting_snapshot(),
        orchestrator_context=context,
        available_tools=[{"name": "workspace_get"}],
    )
    record = get_task_record(task_id)

    assert isinstance(record, dict)
    assert record["operation_contract_fingerprint"] == "fp-store"


def test_register_waiting_task_without_tool_truth_source_stays_backward_compatible(monkeypatch, tmp_path):
    """Bestehende Aufrufer ohne tool_truth_source duerfen nicht brechen -
    Default ist None, kein neuer Pflichtparameter."""
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))

    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    record = get_task_record(task_id)

    assert isinstance(record, dict)
    assert record["tool_truth_source"] is None


def test_claim_waiting_task_is_atomic_and_one_shot(monkeypatch, tmp_path):
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))

    task_id = register_waiting_task(_plan(), _waiting_snapshot())

    claimed = claim_waiting_task(task_id)
    assert isinstance(claimed, dict)
    assert claimed["status"] == "executing"

    stored = get_task_record(task_id)
    assert isinstance(stored, dict)
    assert stored["status"] == "executing"

    try:
        claim_waiting_task(task_id)
        raised = False
    except ValueError as exc:
        raised = True
        assert str(exc) == f"task_not_waiting:{task_id}"

    assert raised is True


def test_claim_rejects_stale_preflight_without_changing_waiting_task(monkeypatch, tmp_path):
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))
    task_id = register_waiting_task(_plan(), _waiting_snapshot())
    before = get_task_record(task_id)

    try:
        claim_waiting_task(task_id, expected_updated_at="stale-version")
        raised = False
    except ValueError as exc:
        raised = True
        assert str(exc) == f"task_changed:{task_id}"

    after = get_task_record(task_id)
    assert raised is True
    assert before == after
    assert after["status"] == TaskLoopState.WAITING.value
