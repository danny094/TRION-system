from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import StepExecutionStatus, TaskToolResult, execute_step
from core.task_loop.run_governor import RUN_GOVERNOR_DEADLINE
from core.task_loop.runner import run_task_loop
from core.task_loop.task_loop import _run_with_replanning
from adapters.task_resume_serialization import snapshot_from_dict, snapshot_to_dict
from tests._task_loop_runner_helpers import _plan, _step


def test_snapshot_roundtrips_deadline_ts():
    snapshot = _snapshot(deadline_ts=1234.5)

    restored = snapshot_from_dict(snapshot_to_dict(snapshot))

    assert restored.deadline_ts == 1234.5


def test_legacy_snapshot_without_deadline_loads_none():
    restored = snapshot_from_dict(
        {
            "plan_id": "plan-1",
            "conversation_id": "conv-1",
            "objective": "legacy",
            "state": "executing",
            "current_step_index": 0,
            "max_steps": 5,
            "max_retries_per_step": 0,
            "max_replans": 1,
        }
    )

    assert restored.deadline_ts is None


def test_step_gate_blocks_past_deadline_before_executing_and_tool_runner():
    events = []
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(deadline_ts=0.0),
        runner,
        event_sink=lambda payload: events.append(dict(payload)),
    )

    assert called["value"] is False
    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.MAX_STEPS_REACHED
    assert result.snapshot.waiting_reason == RUN_GOVERNOR_DEADLINE
    assert "executing" not in [event.get("state") for event in events]


def test_toolcall_gate_blocks_past_deadline_before_tool_start_and_runner():
    events = []
    called = {"value": False}

    def runner(_call):
        called["value"] = True
        return TaskToolResult(success=True, result={"ok": True})

    result = execute_step(
        _step("step-1"),
        runner,
        event_sink=lambda payload: events.append(dict(payload)),
        governor_snapshot=_snapshot(deadline_ts=0.0),
    )

    assert called["value"] is False
    assert result.status == StepExecutionStatus.FAILED
    assert result.error == RUN_GOVERNOR_DEADLINE
    assert result.tool_call_started is False
    assert "tool_start" not in [event.get("type") for event in events]


def test_replan_gate_blocks_past_deadline_before_replanner(monkeypatch):
    called = {"value": False}
    monkeypatch.setattr("core.task_loop.step_governor.current_time_ts", lambda: 50.0)
    monkeypatch.setattr("core.task_loop.toolcall_governor.current_time_ts", lambda: 50.0)
    monkeypatch.setattr("core.task_loop.reflection.current_time_ts", lambda: 101.0)

    def replanner(*_args, **_kwargs):
        called["value"] = True
        return _plan(_step("step-2"))

    result = _run_with_replanning(
        _plan(_step("step-1")),
        _snapshot(deadline_ts=100.0, max_replans=1),
        lambda _call: TaskToolResult(success=False, error="tool_failed"),
        replanner_fn=replanner,
    )

    assert called["value"] is False
    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.REPLAN_BUDGET_EXHAUSTED
    assert result.snapshot.waiting_reason == RUN_GOVERNOR_DEADLINE


def test_future_deadline_allows_existing_path():
    calls = []

    def runner(call):
        calls.append(call.tool_name)
        return TaskToolResult(success=True, result={"ok": True})

    result = run_task_loop(
        _plan(_step("step-1")),
        _snapshot(deadline_ts=4_102_444_800.0),
        runner,
    )

    assert calls == ["demo_tool"]
    assert result.state == TaskLoopState.COMPLETED


def _snapshot(**updates) -> TaskLoopSnapshot:
    data = {
        "plan_id": "plan-1",
        "conversation_id": "conv-1",
        "objective": "governed deadline",
        "state": TaskLoopState.EXECUTING,
        "current_step_index": 0,
        "max_steps": 5,
        "max_retries_per_step": 0,
        "max_replans": 0,
    }
    data.update(updates)
    return TaskLoopSnapshot(**data)
