from dataclasses import replace

from core.task_loop.contracts import StepExecutionStatus, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult, execute_step
from core.task_loop.run_governor import RUN_GOVERNOR_MAX_TOOL_CALLS
from core.task_loop.runner import run_task_loop
from tests._task_loop_runner_helpers import _plan, _step


_TOOL_DETAILS = {"demo_tool": {"name": "demo_tool", "capability_required_args": []}}


def test_executor_blocks_toolcall_governor_before_tool_start_and_runner():
    events = []
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(
        _step("step-1"),
        runner,
        tool_details_by_name=_TOOL_DETAILS,
        event_sink=lambda payload: events.append(dict(payload)),
        governor_snapshot=_snapshot(max_tool_calls=0),
    )

    assert called["value"] is False
    assert result.status == StepExecutionStatus.FAILED
    assert result.error == RUN_GOVERNOR_MAX_TOOL_CALLS
    assert result.tool_call_started is False
    assert [event["type"] for event in events] == ["tool_result"]


def test_runner_counts_allowed_toolcalls_and_blocks_second_call():
    calls = []
    first = run_task_loop(
        _plan(_step("step-1")), _snapshot(max_tool_calls=1), _successful_runner(calls),
        tool_details_by_name=_TOOL_DETAILS,
    )

    assert calls == ["demo_tool"]
    assert first.snapshot.tool_calls == 1

    events = []
    blocked = run_task_loop(
        _plan(_step("step-2")),
        _resume_for_second_step(first.snapshot),
        _successful_runner(calls),
        tool_details_by_name=_TOOL_DETAILS,
        event_sink=lambda payload: events.append(dict(payload)),
    )

    assert calls == ["demo_tool"]
    assert blocked.snapshot.tool_calls == 1
    assert "tool_start" not in [event["type"] for event in events]
    assert any(event.get("type") == "tool_result" for event in events)
    assert all("error" not in event for event in events)


def test_missing_required_args_still_blocks_before_toolcall_governor():
    events = []

    result = execute_step(
        _step("step-1"),
        lambda _call: TaskToolResult(success=True, result={"ok": True}),
        event_sink=lambda payload: events.append(dict(payload)),
        tool_details_by_name={"demo_tool": {"name": "demo_tool", "capability_required_args": ["container_id"]}},
        governor_snapshot=_snapshot(max_tool_calls=0),
    )

    assert result.error == "missing_required_args:container_id"
    assert result.tool_call_started is False
    assert "error" not in events[0]


def _snapshot(**updates) -> TaskLoopSnapshot:
    data = {
        "plan_id": "plan-1",
        "conversation_id": "conv-1",
        "objective": "governed run",
        "state": TaskLoopState.EXECUTING,
        "current_step_index": 0,
        "max_steps": 5,
        "max_retries_per_step": 0,
        "max_replans": 0,
    }
    data.update(updates)
    return TaskLoopSnapshot(**data)


def _resume_for_second_step(snapshot: TaskLoopSnapshot) -> TaskLoopSnapshot:
    return replace(snapshot, state=TaskLoopState.EXECUTING, current_step_index=0, completed_steps=[])


def _successful_runner(calls: list[str]):
    def runner(call):
        calls.append(call.tool_name)
        return TaskToolResult(success=True, result={"ok": True})

    return runner
