from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.run_governor import RUN_GOVERNOR_MAX_TOOL_CALLS, RUN_GOVERNOR_MAX_TOTAL_STEPS
from core.task_loop.runner import run_task_loop
from core.task_loop.task_loop import start_task_loop
from tests._task_loop_runner_helpers import _plan, _step


def test_runner_blocks_total_step_governor_before_executing_and_tool_runner():
    events = []
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(max_total_steps=0),
        runner,
        event_sink=lambda payload: events.append(dict(payload)),
    )

    assert called["value"] is False
    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.MAX_STEPS_REACHED
    assert result.snapshot.total_steps == 0
    assert result.snapshot.waiting_reason == RUN_GOVERNOR_MAX_TOTAL_STEPS
    assert "executing" not in [event.get("state") for event in events]


def test_allowed_step_increments_total_steps():
    result = run_task_loop(_plan(_step("step-1")), _snapshot(max_total_steps=1), _successful_runner)

    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.total_steps == 1


def test_required_args_block_still_counts_started_step():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(max_total_steps=1, max_replans=0),
        _successful_runner,
        tool_details_by_name={"demo_tool": {"name": "demo_tool", "capability_required_args": ["container_id"]}},
    )

    assert result.state == TaskLoopState.BLOCKED
    assert result.snapshot.total_steps == 1
    assert result.snapshot.tool_calls == 0


def test_toolcall_governor_block_counts_step_but_not_toolcall():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(max_total_steps=1, max_tool_calls=0, max_replans=0),
        _successful_runner,
    )

    assert result.state == TaskLoopState.BLOCKED
    assert result.snapshot.total_steps == 1
    assert result.snapshot.tool_calls == 0
    assert result.snapshot.progress_signature.endswith(f":failed:{RUN_GOVERNOR_MAX_TOOL_CALLS}::0")


def test_replan_does_not_reset_total_steps():
    calls = {"count": 0}

    def runner(_call):
        calls["count"] += 1
        if calls["count"] == 1:
            return TaskToolResult(success=False, error="tool_failed")
        return TaskToolResult(success=True, result={"ok": True})

    def replanner(_plan, **_kwargs):
        return _plan.__class__(
            intent="run_tools",
            steps=[_step("step-2")],
            needs_task_loop=True,
            risk_level=_plan.risk_level,
            plan_id="plan-2",
        )

    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="replan once",
        tool_runner=runner,
        replanner_fn=replanner,
        max_steps=5,
        max_replans=1,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.total_steps == 2


def test_existing_total_steps_blocks_resume_snapshot_at_limit():
    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(total_steps=1, max_total_steps=1),
        _successful_runner,
    )

    assert result.state == TaskLoopState.BLOCKED
    assert result.snapshot.total_steps == 1
    assert result.snapshot.waiting_reason == RUN_GOVERNOR_MAX_TOTAL_STEPS


def _snapshot(**updates) -> TaskLoopSnapshot:
    data = {
        "plan_id": "plan-1",
        "conversation_id": "conv-1",
        "objective": "governed steps",
        "state": TaskLoopState.EXECUTING,
        "current_step_index": 0,
        "max_steps": 5,
        "max_retries_per_step": 0,
        "max_replans": 0,
    }
    data.update(updates)
    return TaskLoopSnapshot(**data)


def _successful_runner(_call):
    return TaskToolResult(success=True, result={"ok": True})
