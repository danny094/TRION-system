import importlib.util
import json
from dataclasses import replace
from enum import Enum
from pathlib import Path

import pytest

from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from core.task_loop.provenance_trace import task_loop_provenance_event


class ForeignState(str, Enum):
    VALUE = "FOREIGN_STATE_SENTINEL"


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conversation-1",
        objective="internal objective",
        state=TaskLoopState.EXECUTING,
        current_step_index=0,
        max_steps=2,
        max_retries_per_step=0,
    )


def _event_to_ndjson(payload: dict) -> str:
    path = Path(__file__).resolve().parents[1] / "adapters" / "admin-api" / "chat_stream.py"
    spec = importlib.util.spec_from_file_location("task_loop_state_projection_stream", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.event_to_ndjson("model", "conversation-1", payload)


def test_malformed_state_sentinels_fail_closed_through_ndjson():
    snapshot = replace(
        _snapshot(),
        state="CURRENT_STATE_SENTINEL",
        previous_state="PREVIOUS_STATE_SENTINEL",
    )

    event = task_loop_provenance_event(snapshot)
    serialized = _event_to_ndjson(event)
    payload = json.loads(serialized)

    assert payload["transition_present"] is False
    assert payload["transition_from"] is None
    assert payload["transition_to"] is None
    assert payload["type"] == "task_loop_provenance"
    assert "STATE_SENTINEL" not in serialized


@pytest.mark.parametrize("value", ["unknown", True, 1, {}, [], ForeignState.VALUE, object()])
def test_foreign_state_types_are_not_stringified(value):
    event = task_loop_provenance_event(replace(_snapshot(), state=value, previous_state=value))
    serialized = json.dumps(event, ensure_ascii=False)

    assert event["transition_present"] is False
    assert event["transition_from"] is None
    assert event["transition_to"] is None
    assert "FOREIGN_STATE_SENTINEL" not in serialized


def test_real_transition_retains_fixed_state_values():
    event = task_loop_provenance_event(_snapshot().transition_to(TaskLoopState.REFLECTING))

    assert event["transition_present"] is True
    assert event["transition_from"] == "executing"
    assert event["transition_to"] == "reflecting"
