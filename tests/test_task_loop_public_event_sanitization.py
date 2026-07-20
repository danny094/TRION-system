import json

from adapters.task_resume_events import waiting_result_event_payload
from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_task_loop_state


def _waiting_result() -> TaskLoopResult:
    snapshot = TaskLoopSnapshot(
        plan_id="PLAN_ID_SENTINEL", conversation_id="CONVERSATION_ID_SENTINEL",
        objective="USER_TEXT_SENTINEL",
        state=TaskLoopState.WAITING, current_step_index=0, max_steps=3,
        max_retries_per_step=0, waiting_reason="plan_contract_unknown_tool:PRIVATE_TOOL_SENTINEL",
        waiting_source="SECRET_SENTINEL", pending_step="PENDING_STEP_SENTINEL",
        completed_steps=["COMPLETED_STEP_SENTINEL"],
    )
    return TaskLoopResult(
        state=TaskLoopState.WAITING, stop_reason=StopReason.CAPABILITY_GAP,
        artifacts=[], visible_content="waiting", snapshot=snapshot,
    )


def test_task_loop_state_omits_free_waiting_values():
    events = []
    emit_task_loop_state(events.append, _waiting_result().snapshot, total_steps=1)

    payload = events[0]
    serialized = json.dumps(payload)
    assert payload["type"] == "task_loop_state"
    assert payload["state"] == "waiting"
    assert "waiting_reason" not in payload
    assert "waiting_source" not in payload
    assert payload["completed_count"] == 1
    for field in ("plan_id", "step_id", "pending_step", "completed_steps"):
        assert field not in payload
    assert "SENTINEL" not in serialized


def test_task_loop_waiting_payload_omits_free_waiting_values():
    payload = waiting_result_event_payload("task-safe", _waiting_result())
    serialized = json.dumps(payload)

    assert payload["type"] == "task_loop_waiting"
    assert payload["state"] == "waiting"
    assert payload["stop_reason"] == "capability_gap"
    assert "waiting_reason" not in payload
    assert "waiting_source" not in payload
    assert payload["task_id"] == "task-safe"
    assert payload["completed_count"] == 1
    for field in ("plan_id", "conversation_id", "pending_step", "completed_steps"):
        assert field not in payload
    assert "SENTINEL" not in serialized
