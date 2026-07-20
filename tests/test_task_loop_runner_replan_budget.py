from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.runner import run_task_loop
from tests._task_loop_runner_helpers import _plan, _step


def test_run_task_loop_increments_replan_count():
    result = run_task_loop(_plan(_step("step-1")), _snapshot(max_replans=2), _failing_runner)

    assert result.state == TaskLoopState.REPLANNING
    assert result.stop_reason == StopReason.STEP_FAILED
    assert result.snapshot.replan_count == 1


def test_run_task_loop_blocks_when_replan_budget_is_exhausted():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(replan_count=2, max_replans=2, objective="Stop after replans"),
        _failing_runner,
    )

    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED
    assert result.snapshot.replan_count == 2


def test_run_task_loop_blocks_when_replan_budget_is_zero():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(replan_count=50, max_replans=0, objective="Do not replan"),
        _failing_runner,
    )

    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED
    assert result.snapshot.replan_count == 50


def test_run_task_loop_allows_first_replan_with_positive_budget():
    result = run_task_loop(_plan(_step("step-1")), _snapshot(max_replans=1), _failing_runner)

    assert result.state == TaskLoopState.REPLANNING
    assert result.stop_reason == StopReason.STEP_FAILED
    assert result.snapshot.replan_count == 1


def test_run_task_loop_waits_when_failure_escalation_is_ask():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(max_replans=2, failure_escalation="ask", objective="Need guidance after failure"),
        _failing_runner,
    )

    assert result.state == TaskLoopState.WAITING
    assert result.stop_reason == StopReason.USER_DECISION_NEEDED
    assert result.snapshot.waiting_reason == "step_failed_user_decision"
    assert result.snapshot.waiting_source == "failure_policy"


def test_run_task_loop_blocks_when_failure_escalation_is_abort():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(max_replans=2, failure_escalation="abort", objective="Stop on first hard failure"),
        _failing_runner,
    )

    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.FAILURE_ABORT_POLICY


def _snapshot(**updates) -> TaskLoopSnapshot:
    data = {
        "plan_id": "plan-1",
        "conversation_id": "conv-1",
        "objective": "Need replanning",
        "state": TaskLoopState.EXECUTING,
        "current_step_index": 0,
        "max_steps": 5,
        "max_retries_per_step": 0,
    }
    data.update(updates)
    return TaskLoopSnapshot(**data)


def _failing_runner(call):
    return TaskToolResult(success=False, error="tool_failed")
