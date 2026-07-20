from collections.abc import Iterable, Mapping
from typing import Any

_REQUIRED_FIELDS = (
    "name",
    "capability_domain",
    "capability_operation",
    "capability_evidence_types",
    "capability_required_args",
    "capability_target_scopes",
    "capability_risk",
)
_ALLOW_EMPTY_LIST_FIELDS = {"capability_required_args"}


def validate_plan_step_ids(plan: Any) -> str:
    step_ids = [getattr(step, "step_id", None) for step in list(getattr(plan, "steps", []) or [])]
    if any(type(step_id) is not str or not step_id or step_id != step_id.strip() for step_id in step_ids):
        return "plan_contract_invalid_step_id"
    if len(set(step_ids)) != len(step_ids):
        return "plan_contract_duplicate_step_id"
    return ""


def validate_tool_metadata(planned_tools: Iterable[str], tool_truth: Any) -> str:
    details = _details_by_name(tool_truth)
    for tool in planned_tools:
        detail = details.get(tool)
        if detail is None:
            return f"plan_contract_missing_tool_detail:{tool}"
        missing = _missing_field(detail)
        if missing:
            return f"plan_contract_missing_tool_metadata:{tool}:{missing}"
    return ""


def _details_by_name(tool_truth: Any) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for item in _as_iterable(tool_truth):
        if isinstance(item, str):
            continue
        name = _field_value(item, "name")
        if isinstance(name, str) and name.strip():
            details[name.strip()] = item
    return details


def _missing_field(detail: Any) -> str:
    for field in _REQUIRED_FIELDS:
        if not _has_required_value(detail, field):
            return field
    return ""


def _has_required_value(detail: Any, field: str) -> bool:
    value = _field_value(detail, field, missing_marker=True)
    if value is _MISSING:
        return False
    if field in _ALLOW_EMPTY_LIST_FIELDS:
        return isinstance(value, list)
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())


_MISSING = object()


def _field_value(detail: Any, field: str, *, missing_marker: bool = False) -> Any:
    default = _MISSING if missing_marker else ""
    if isinstance(detail, Mapping):
        return detail.get(field, default)
    return getattr(detail, field, default)


def _as_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        return []
    return value
