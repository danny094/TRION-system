from adapters.task_resume_serialization import snapshot_from_dict, snapshot_to_dict
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState


def _snapshot(**updates) -> TaskLoopSnapshot:
    data = {
        "plan_id": "plan-governor",
        "conversation_id": "conv-governor",
        "objective": "Run with governor counters",
        "state": TaskLoopState.EXECUTING,
        "current_step_index": 0,
        "max_steps": 5,
        "max_retries_per_step": 1,
    }
    data.update(updates)
    return TaskLoopSnapshot(**data)


def test_task_loop_snapshot_governor_defaults_are_backward_compatible():
    snapshot = _snapshot()

    assert snapshot.total_steps == 0
    assert snapshot.tool_calls == 0
    assert snapshot.max_total_steps is None
    assert snapshot.max_tool_calls is None


def test_snapshot_roundtrip_preserves_governor_counters_and_limits():
    snapshot = _snapshot(
        total_steps=7,
        tool_calls=3,
        max_total_steps=9,
        max_tool_calls=4,
    )

    parsed = snapshot_from_dict(snapshot_to_dict(snapshot))

    assert parsed.total_steps == 7
    assert parsed.tool_calls == 3
    assert parsed.max_total_steps == 9
    assert parsed.max_tool_calls == 4


def test_legacy_snapshot_dict_without_governor_fields_uses_defaults():
    parsed = snapshot_from_dict(
        {
            "plan_id": "legacy",
            "conversation_id": "conv",
            "objective": "legacy record",
            "state": "waiting",
            "current_step_index": 0,
            "max_steps": 5,
            "max_retries_per_step": 1,
        }
    )

    assert parsed.total_steps == 0
    assert parsed.tool_calls == 0
    assert parsed.max_total_steps is None
    assert parsed.max_tool_calls is None
