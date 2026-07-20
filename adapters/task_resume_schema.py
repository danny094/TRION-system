"""Strict schema parsing for internal task-resume records."""
from typing import Any

from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import ThinkingPlan
from adapters.task_resume_receipts import step_operation_executions


_NO_DEFAULT = object()
_MISSING = object()


def parse_plan(data: Any) -> ThinkingPlan:
    plan = ThinkingPlan.from_dict(data)
    if plan is None:
        raise ValueError("invalid_plan")
    return plan


def parse_snapshot(data: dict[str, Any]) -> TaskLoopSnapshot:
    _require_dict(data, "snapshot")
    return TaskLoopSnapshot(
        plan_id=_string(_field(data, "plan_id"), "plan_id"),
        conversation_id=_string(_field(data, "conversation_id"), "conversation_id"),
        objective=_string(_field(data, "objective"), "objective"),
        state=_enum(_field(data, "state"), TaskLoopState, "state"),
        current_step_index=_int(_field(data, "current_step_index"), "current_step_index", 0),
        max_steps=_int(_field(data, "max_steps"), "max_steps", 1),
        max_retries_per_step=_int(_field(data, "max_retries_per_step"), "max_retries_per_step", 0),
        total_steps=_int(_field(data, "total_steps", 0), "total_steps", 0),
        tool_calls=_int(_field(data, "tool_calls", 0), "tool_calls", 0),
        max_total_steps=_optional_int(_field(data, "max_total_steps", None), "max_total_steps"),
        max_tool_calls=_optional_int(_field(data, "max_tool_calls", None), "max_tool_calls"),
        deadline_ts=_optional_number(_field(data, "deadline_ts", None), "deadline_ts"),
        replan_count=_int(_field(data, "replan_count", 0), "replan_count", 0),
        max_replans=_int(_field(data, "max_replans", 0), "max_replans", 0),
        loop_detection_enabled=_bool(_field(data, "loop_detection_enabled", True), "loop_detection_enabled"),
        no_progress_threshold=_int(_field(data, "no_progress_threshold", 3), "no_progress_threshold", 2),
        approval_mode=_choice(_field(data, "approval_mode", "risk_based"), "approval_mode", {"approval_first", "risk_based", "permissive"}),
        failure_escalation=_choice(_field(data, "failure_escalation", "replan"), "failure_escalation", {"replan", "ask", "abort"}),
        approval_required_tools=_string_list(_field(data, "approval_required_tools", []), "approval_required_tools"),
        completed_steps=_string_list(_field(data, "completed_steps", []), "completed_steps", nonempty=True),
        pending_step=_string(_field(data, "pending_step", ""), "pending_step", trimmed=True),
        artifacts=_list(_field(data, "artifacts", []), "artifacts"),
        stop_reason=_optional_enum(_field(data, "stop_reason", None), StopReason, "stop_reason"),
        waiting_reason=_optional_string(_field(data, "waiting_reason", None), "waiting_reason"),
        waiting_source=_optional_string(_field(data, "waiting_source", None), "waiting_source"),
        error_count=_int(_field(data, "error_count", 0), "error_count", 0),
        retry_counts=_int_dict(_field(data, "retry_counts", {}), "retry_counts"),
        progress_signature=_string(_field(data, "progress_signature", ""), "progress_signature"),
        no_progress_count=_int(_field(data, "no_progress_count", 0), "no_progress_count", 0),
        previous_state=_optional_enum(_field(data, "previous_state", None), TaskLoopState, "previous_state"),
        step_operation_executions=_execution_history(data),
    )


def _execution_history(data: dict[str, Any]):
    value = _field(data, "step_operation_executions", _MISSING)
    return [] if value is _MISSING else step_operation_executions(value)


def _field(data: dict[str, Any], name: str, default: Any = _NO_DEFAULT) -> Any:
    if name in data:
        return data[name]
    if default is _NO_DEFAULT:
        raise ValueError(f"missing_{name}")
    return default


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"invalid_{name}")
    return value


def _string(value: Any, name: str, *, nonempty: bool = False, trimmed: bool = False) -> str:
    if type(value) is not str or (nonempty and not value) or (trimmed and value != value.strip()):
        raise ValueError(f"invalid_{name}")
    return value


def _optional_string(value: Any, name: str, *, nonempty: bool = False, trimmed: bool = False) -> str | None:
    return None if value is None else _string(value, name, nonempty=nonempty, trimmed=trimmed)


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"invalid_{name}")
    return value


def _int(value: Any, name: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"invalid_{name}")
    return value


def _optional_int(value: Any, name: str) -> int | None:
    return None if value is None else _int(value, name, 0)


def _optional_number(value: Any, name: str) -> int | float | None:
    if value is None:
        return None
    if type(value) not in {int, float}:
        raise ValueError(f"invalid_{name}")
    return value


def _enum(value: Any, enum_type: Any, name: str) -> Any:
    if type(value) is not str:
        raise ValueError(f"invalid_{name}")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"invalid_{name}") from exc


def _optional_enum(value: Any, enum_type: Any, name: str) -> Any:
    return None if value is None else _enum(value, enum_type, name)


def _choice(value: Any, name: str, allowed: set[str]) -> str:
    if type(value) is not str or value not in allowed:
        raise ValueError(f"invalid_{name}")
    return value


def _dict(value: Any, name: str) -> dict[str, Any]:
    return dict(_require_dict(value, name))


def _list(value: Any, name: str) -> list[Any]:
    if type(value) is not list:
        raise ValueError(f"invalid_{name}")
    return list(value)


def _string_list(value: Any, name: str, *, nonempty: bool = False) -> list[str]:
    items = _list(value, name)
    for item in items:
        _string(item, name, nonempty=nonempty, trimmed=nonempty)
    return items


def _int_dict(value: Any, name: str) -> dict[str, int]:
    data = _dict(value, name)
    for key, item in data.items():
        _string(key, name, nonempty=True, trimmed=True)
        _int(item, name, 0)
    return data
