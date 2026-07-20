from core.task_loop.run_governor import (
    RUN_GOVERNOR_CANCELLED,
    RUN_GOVERNOR_DEADLINE,
    RUN_GOVERNOR_MAX_REPLANS,
    RUN_GOVERNOR_MAX_TOOL_CALLS,
    RUN_GOVERNOR_MAX_TOTAL_STEPS,
    RunGovernorState,
    can_replan,
    can_start_step,
    can_start_tool_call,
    run_governor_from_snapshot,
    replan_governor_from_snapshot,
)
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState


def test_missing_limits_allow_actions():
    state = RunGovernorState(total_steps=500, tool_calls=500, replans=500)

    assert can_start_step(state).allowed is True
    assert can_start_tool_call(state).allowed is True
    assert can_replan(state).allowed is True


def test_max_replans_none_allows_replan():
    state = RunGovernorState(replans=99, max_replans=None)

    assert can_replan(state).allowed is True


def test_max_replans_zero_blocks_replan():
    decision = can_replan(RunGovernorState(max_replans=0))

    assert decision.allowed is False
    assert decision.reason == RUN_GOVERNOR_MAX_REPLANS


def test_max_replans_one_allows_first_and_blocks_after_increment():
    state = RunGovernorState(max_replans=1)

    assert can_replan(state).allowed is True
    blocked = can_replan(state.with_replan())
    assert blocked.allowed is False
    assert blocked.reason == RUN_GOVERNOR_MAX_REPLANS


def test_max_tool_calls_zero_blocks_tool_call():
    decision = can_start_tool_call(RunGovernorState(max_tool_calls=0))

    assert decision.allowed is False
    assert decision.reason == RUN_GOVERNOR_MAX_TOOL_CALLS


def test_max_total_steps_zero_blocks_step():
    decision = can_start_step(RunGovernorState(max_total_steps=0))

    assert decision.allowed is False
    assert decision.reason == RUN_GOVERNOR_MAX_TOTAL_STEPS


def test_cancelled_blocks_all_actions():
    state = RunGovernorState(cancelled=True)

    assert can_start_step(state).reason == RUN_GOVERNOR_CANCELLED
    assert can_start_tool_call(state).reason == RUN_GOVERNOR_CANCELLED
    assert can_replan(state).reason == RUN_GOVERNOR_CANCELLED


def test_past_deadline_blocks_actions():
    state = RunGovernorState(deadline_ts=10.0)

    assert can_start_step(state, now_ts=10.0).reason == RUN_GOVERNOR_DEADLINE
    assert can_start_tool_call(state, now_ts=11.0).reason == RUN_GOVERNOR_DEADLINE
    assert can_replan(state, now_ts=12.0).reason == RUN_GOVERNOR_DEADLINE


def test_replan_governor_from_snapshot_preserves_zero_limit():
    snapshot = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="test",
        state=TaskLoopState.REFLECTING,
        current_step_index=0,
        max_steps=3,
        max_retries_per_step=0,
        max_replans=0,
    )

    decision = can_replan(replan_governor_from_snapshot(snapshot))

    assert decision.allowed is False
    assert decision.reason == RUN_GOVERNOR_MAX_REPLANS


def test_run_governor_from_snapshot_reads_global_counters_and_limits():
    snapshot = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="test",
        state=TaskLoopState.EXECUTING,
        current_step_index=0,
        max_steps=3,
        max_retries_per_step=0,
        total_steps=4,
        tool_calls=2,
        max_total_steps=5,
        max_tool_calls=3,
        replan_count=1,
        max_replans=2,
    )

    state = run_governor_from_snapshot(snapshot)

    assert state.total_steps == 4
    assert state.tool_calls == 2
    assert state.max_total_steps == 5
    assert state.max_tool_calls == 3
    assert state.replans == 1
    assert state.max_replans == 2
