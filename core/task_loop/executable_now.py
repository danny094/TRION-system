from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ExecutableNowDecision:
    allowed: bool
    missing_args: list[str] = field(default_factory=list)
    error: str = ""


def check_executable_now(
    tool_call: Any,
    tool_details_by_name: Mapping[str, Mapping[str, Any]] | None,
) -> ExecutableNowDecision:
    if tool_details_by_name is None:
        return ExecutableNowDecision(
            allowed=False,
            error="missing_tool_metadata",
        )
    tool_name = str(getattr(tool_call, "tool_name", "") or "").strip()
    detail = tool_details_by_name.get(tool_name)
    if not isinstance(detail, Mapping):
        return ExecutableNowDecision(
            allowed=False,
            error="missing_tool_metadata",
        )
    required = _required_args(detail)
    arguments = getattr(tool_call, "arguments", {})
    missing = [arg for arg in required if not _has_bound_arg(arguments, arg)]
    if missing:
        return ExecutableNowDecision(
            allowed=False,
            missing_args=missing,
            error=f"missing_required_args:{','.join(missing)}",
        )
    return ExecutableNowDecision(allowed=True)


def details_by_name(tools: Any) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for item in list(tools or []):
        detail = _detail_mapping(item)
        name = str(detail.get("name") or getattr(item, "name", "") or "").strip()
        if name:
            result[name] = detail
    return result


def _detail_mapping(item: Any) -> Mapping[str, Any]:
    if isinstance(item, Mapping):
        if item.get("capability_required_args") is not None:
            return item
        intent = item.get("tool_intent")
        if isinstance(intent, Mapping):
            return {**dict(item), "capability_required_args": list(intent.get("requires") or [])}
        return item
    return {
        "name": getattr(item, "name", ""),
        "capability_required_args": getattr(item, "capability_required_args", []),
        "capability_evidence_types": getattr(item, "capability_evidence_types", []),
        "capability_output_schema": str(getattr(item, "capability_output_schema", "") or ""),
        "output_schema": deepcopy(getattr(item, "output_schema", {}) or {}),
    }


def _required_args(detail: Mapping[str, Any]) -> list[str]:
    return [
        str(item).strip()
        for item in list(detail.get("capability_required_args") or [])
        if str(item).strip()
    ]


def _has_bound_arg(arguments: Mapping[str, Any], required_arg: str) -> bool:
    for key in _argument_keys(required_arg):
        value = arguments.get(key)
        if value is not None and str(value).strip():
            return True
    return False


def _argument_keys(required_arg: str) -> tuple[str, ...]:
    if required_arg == "container_id_or_name":
        return ("container_id_or_name", "container_id", "container_name")
    return (required_arg,)
