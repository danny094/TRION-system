from dataclasses import replace

from core.task_loop.completion_gate import finalize_completion
from core.task_loop.contracts import CompletionStatus, StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.run_governor import RUN_GOVERNOR_DEADLINE
from core.thinking.contracts import AdditionalEvidenceNeed, PlanStep, RiskLevel, ThinkingPlan


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="answer",
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        steps=[PlanStep(step_id="step-1", title="Step", goal="Do work")],
        additional_evidence_need=AdditionalEvidenceNeed(
            kind="file_read",
            candidate_tools=["file_read"],
        ),
    )


def _snapshot(**updates) -> TaskLoopSnapshot:
    base = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="answer",
        state=TaskLoopState.COMPLETED,
        current_step_index=1,
        max_steps=3,
        max_retries_per_step=0,
        completed_steps=["step-1"],
        max_replans=1,
    )
    return replace(base, **updates)


def test_completion_gate_blocks_additional_evidence_replan_when_governor_denies_zero():
    result, synthetic = finalize_completion(_plan(), _snapshot(max_replans=0), total_steps=1)

    assert result.completion_status == CompletionStatus.BLOCKED
    assert result.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED
    assert result.snapshot.replan_count == 0
    assert synthetic is None


def test_completion_gate_allows_additional_evidence_replan_when_limit_is_none():
    result, synthetic = finalize_completion(_plan(), _snapshot(max_replans=None), total_steps=1)

    assert result.completion_status == CompletionStatus.NEEDS_MORE_EVIDENCE
    assert result.stop_reason == StopReason.ADDITIONAL_EVIDENCE_REQUIRED
    assert result.snapshot.replan_count == 1
    assert synthetic is not None


def test_completion_gate_deadline_blocks_additional_evidence_replan(monkeypatch):
    monkeypatch.setattr("core.task_loop.completion_gate.current_time_ts", lambda: 101.0)

    result, synthetic = finalize_completion(_plan(), _snapshot(deadline_ts=100.0), total_steps=1)

    assert result.completion_status == CompletionStatus.BLOCKED
    assert result.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED
    assert result.snapshot.waiting_reason == RUN_GOVERNOR_DEADLINE
    assert result.snapshot.replan_count == 0
    assert synthetic is None
