from core.task_loop.contracts import TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import RiskLevel, ThinkingPlan
from tests._task_loop_runner_helpers import _plan, _step


def test_start_task_loop_emits_zero_based_index_for_replanned_to_answer_completion():
    events = []
    replanned = ThinkingPlan(
        intent="answer_user",
        steps=[_step("answer_user", tool=None)],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-answer",
    )

    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="Need a final answer",
        tool_runner=lambda call: TaskToolResult(success=False, error="tool_failed"),
        replanner_fn=lambda *args, **kwargs: replanned,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=2,
        event_sink=lambda payload: events.append(dict(payload)),
    )

    latest = [event for event in events if event.get("type") == "task_loop_state"][-1]
    assert result.state == TaskLoopState.COMPLETED
    assert latest["state"] == "completed"
    assert "step_title" not in latest
    assert latest["step_index"] == 0
    assert latest["total_steps"] == 1


def test_start_task_loop_emits_zero_based_index_for_single_step_completion():
    events = []

    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="Run one step",
        tool_runner=lambda call: TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]}),
        max_steps=5,
        max_replans=2,
        event_sink=lambda payload: events.append(dict(payload)),
    )

    latest = [event for event in events if event.get("type") == "task_loop_state"][-1]
    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.current_step_index == 1
    assert latest["state"] == "completed"
    assert "step_title" not in latest
    assert latest["step_index"] == 0
    assert latest["total_steps"] == 1


def test_start_task_loop_emits_state_events():
    events = []

    result = start_task_loop(
        _plan(_step("step-1"), _step("step-2")),
        conversation_id="conv-1",
        objective="Emit state events",
        tool_runner=lambda call: TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]}),
        event_sink=lambda payload: events.append(dict(payload)),
    )

    states = [event.get("state") for event in events if event.get("type") == "task_loop_state"]
    assert result.state == TaskLoopState.COMPLETED
    assert states[0] == "executing"
    assert states[-1] == "completed"
