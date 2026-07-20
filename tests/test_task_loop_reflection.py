from dataclasses import replace

from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.reflection import ReflectionAction, evaluate


def _snapshot(**updates) -> TaskLoopSnapshot:
    base = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="Original user objective",
        state=TaskLoopState.REFLECTING,
        current_step_index=0,
        max_steps=10,
        max_retries_per_step=1,
        max_replans=2,
    )
    return replace(base, **updates)


def _result(status=StepExecutionStatus.SUCCESS, step_id="step-1", **updates) -> StepExecutionResult:
    base = StepExecutionResult(step_id=step_id, status=status, output={"ok": True})
    return replace(base, **updates)


def test_success_continues_when_steps_remain():
    decision = evaluate(_result(), _snapshot(current_step_index=0), total_steps=2)

    assert decision.action == ReflectionAction.CONTINUE
    assert decision.stop_reason is None


def test_success_completes_on_last_step():
    decision = evaluate(_result(), _snapshot(current_step_index=1), total_steps=2)

    assert decision.action == ReflectionAction.COMPLETED
    assert decision.stop_reason is None


def test_failed_step_retries_until_budget_is_used():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="temporary"),
        _snapshot(max_retries_per_step=2, retry_counts={"step-1": 1}),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.CONTINUE
    assert decision.retry_counts == {"step-1": 2}


def test_failed_step_replans_when_retry_budget_is_exhausted():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="permanent"),
        _snapshot(max_retries_per_step=1, retry_counts={"step-1": 1}),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.REPLAN
    assert decision.stop_reason == StopReason.STEP_FAILED


def test_failed_step_blocks_when_replan_budget_is_exhausted():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="permanent"),
        _snapshot(max_retries_per_step=1, retry_counts={"step-1": 1}, replan_count=2, max_replans=2),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.BLOCK
    assert decision.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED


def test_failed_step_waits_when_error_behavior_prefers_ask():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="needs input"),
        _snapshot(max_retries_per_step=0, failure_escalation="ask"),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.WAITING
    assert decision.stop_reason == StopReason.USER_DECISION_NEEDED
    assert decision.waiting_reason == "step_failed_user_decision"
    assert decision.waiting_source == "failure_policy"


def test_failed_step_blocks_when_error_behavior_prefers_abort():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="fatal"),
        _snapshot(max_retries_per_step=0, failure_escalation="abort"),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.BLOCK
    assert decision.stop_reason == StopReason.FAILURE_ABORT_POLICY


def test_failed_step_blocks_when_replan_budget_is_zero():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="permanent"),
        _snapshot(max_retries_per_step=1, retry_counts={"step-1": 1}, replan_count=99, max_replans=0),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.BLOCK
    assert decision.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED


def test_failed_step_allows_replan_when_replan_budget_is_none():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="permanent"),
        _snapshot(max_retries_per_step=1, retry_counts={"step-1": 1}, replan_count=99, max_replans=None),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.REPLAN
    assert decision.stop_reason == StopReason.STEP_FAILED


def test_skipped_step_waits_for_user_decision():
    decision = evaluate(_result(status=StepExecutionStatus.SKIPPED), _snapshot(), total_steps=2)

    assert decision.action == ReflectionAction.WAITING
    assert decision.stop_reason == StopReason.USER_DECISION_NEEDED


def test_max_steps_blocks_before_more_work():
    decision = evaluate(_result(), _snapshot(current_step_index=9, max_steps=10), total_steps=20)

    assert decision.action == ReflectionAction.BLOCK
    assert decision.stop_reason == StopReason.MAX_STEPS_REACHED


def test_repeated_same_signature_blocks_as_no_progress():
    first = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="same"),
        _snapshot(progress_signature="step-1:failed:same:ok:0", no_progress_count=2, no_progress_threshold=3),
        total_steps=2,
    )

    assert first.action == ReflectionAction.BLOCK
    assert first.stop_reason == StopReason.NO_PROGRESS
    assert first.no_progress_count == 3


def test_repeated_same_signature_does_not_block_when_loop_detection_disabled():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="same"),
        _snapshot(
            progress_signature="step-1:failed:same:ok:0",
            no_progress_count=9,
            max_retries_per_step=0,
            loop_detection_enabled=False,
        ),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.REPLAN
    assert decision.stop_reason == StopReason.STEP_FAILED


def test_repeated_same_signature_uses_configured_threshold():
    decision = evaluate(
        _result(status=StepExecutionStatus.FAILED, error="same"),
        _snapshot(
            progress_signature="step-1:failed:same:ok:0",
            no_progress_count=1,
            max_retries_per_step=0,
            no_progress_threshold=5,
        ),
        total_steps=2,
    )

    assert decision.action == ReflectionAction.REPLAN
    assert decision.stop_reason == StopReason.STEP_FAILED
