"""Fail-closed public projections for TaskLoop event metadata."""
from typing import Any

from core.task_loop.contracts import StepExecutionStatus


def public_waiting_fields(reason: Any, source: Any) -> dict[str, str]:
    """Free internal waiting strings have no public schema representation."""
    del reason, source
    return {}


def public_replan_trigger(failure: Any) -> str:
    """Project failures to fixed categories without parsing payload values."""
    if failure is None:
        return ""
    error = str(getattr(failure, "error", "") or "")
    if error.startswith("objective_not_met:"):
        return "objective_not_met"
    if error.startswith("additional_evidence_needed:"):
        return "additional_evidence_needed"
    if error.startswith("{"):
        return "structured_error"
    status = getattr(failure, "status", None)
    if isinstance(status, StepExecutionStatus):
        return f"step_failed:{status.value}"
    return "step_failed:unknown" if status is not None else "unknown_error"
