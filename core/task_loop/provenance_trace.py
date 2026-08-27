"""Sanitized TaskLoop transition provenance.

Observe-only projection for chat trace events. It reads existing snapshots,
plans and controlled failure categories, but never tool arguments, targets,
artifact contents, user text or output text.
"""
from __future__ import annotations

from typing import Any

from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from core.task_loop.event_sanitization import public_replan_trigger


def task_loop_provenance_event(
    snapshot: TaskLoopSnapshot,
    *,
    phase: str = "state",
    plan: Any = None,
    failure: Any = None,
    validator_decision: str = "",
) -> dict[str, Any]:
    return {
        "type": "task_loop_provenance",
        "stage": "task_loop",
        "phase": _clean(phase) or "state",
        **_transition_projection(snapshot),
        **_replan_projection(snapshot, plan, failure, validator_decision),
    }


def _transition_projection(snapshot: TaskLoopSnapshot) -> dict[str, Any]:
    previous = _state_value(getattr(snapshot, "previous_state", None))
    return {
        "transition_present": previous is not None,
        "transition_from": previous,
        "transition_to": _state_value(getattr(snapshot, "state", None)),
    }


def _replan_projection(
    snapshot: TaskLoopSnapshot,
    plan: Any,
    failure: Any,
    validator_decision: str,
) -> dict[str, Any]:
    inferred_decision = _validator_decision(snapshot, validator_decision)
    required_count = len({
        _clean(item)
        for step in list(getattr(plan, "steps", []) or [])
        for item in list(getattr(step, "required_evidence", []) or [])
        if _clean(item) and _clean(item) != "tool_result"
    })
    return {
        "replan_proposed": _clean(validator_decision) == "approved" or _state_value(getattr(snapshot, "state", None)) == "replanning",
        "validator_decision": inferred_decision,
        "replan_trigger": public_replan_trigger(failure),
        "replanned_required_evidence_present": required_count > 0,
        "replanned_required_evidence_count": required_count,
    }


def _validator_decision(snapshot: TaskLoopSnapshot, explicit: str) -> str:
    value = _clean(explicit)
    if value:
        return value
    if _clean(getattr(snapshot, "waiting_source", "")) == "plan_contract_validator":
        return "blocked"
    return ""


def _state_value(value: Any) -> str | None:
    return value.value if type(value) is TaskLoopState else None


def _clean(value: Any) -> str:
    return str(value or "").strip()
