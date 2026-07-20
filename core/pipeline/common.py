from dataclasses import asdict
from enum import Enum
from collections.abc import Mapping
from typing import Any, Dict


_PUBLIC_SNAPSHOT_FIELDS = (
    "state", "stop_reason", "current_step_index", "max_steps", "total_steps",
    "tool_calls", "max_total_steps", "max_tool_calls", "replan_count",
    "max_replans", "no_progress_count", "error_count",
)
_PUBLIC_ARTIFACT_TYPES = frozenset({"file_content", "semantic_search_result", "tool_result"})


def contract_dict(value: Any) -> Dict[str, Any]:
    def convert(item: Any) -> Any:
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, dict):
            return {key: convert(val) for key, val in item.items()}
        if isinstance(item, list):
            return [convert(val) for val in item]
        return item

    data = asdict(value)
    return convert(data)


def public_task_loop_snapshot(snapshot: Any) -> Dict[str, Any]:
    """Expose only stable status and counter fields from a task snapshot."""
    data = contract_dict(snapshot)
    public = {key: data.get(key) for key in _PUBLIC_SNAPSHOT_FIELDS}
    public["artifacts"] = public_task_artifacts(data.get("artifacts"))
    return public


def public_task_artifacts(artifacts: Any) -> list[Dict[str, str]]:
    """Project artifacts to controlled type labels without payload metadata."""
    if not isinstance(artifacts, list):
        return []
    public: list[Dict[str, str]] = []
    for item in artifacts:
        if not isinstance(item, Mapping):
            continue
        artifact_type = str(item.get("artifact_type") or "").strip()
        public.append({"artifact_type": artifact_type if artifact_type in _PUBLIC_ARTIFACT_TYPES else "artifact"})
    return public


def merge_thinking_contexts(*contexts: Dict[str, Any] | None) -> Dict[str, Any] | None:
    merged: Dict[str, Any] = {
        "available_tools": [],
        "selected_tools": [],
        "available_tool_details": [],
        "selected_tool_details": [],
        "context": {},
    }
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for key in ("available_tools", "selected_tools"):
            for item in list(context.get(key) or []):
                if item not in merged[key]:
                    merged[key].append(item)
        for key in ("available_tool_details", "selected_tool_details"):
            for item in list(context.get(key) or []):
                if item not in merged[key]:
                    merged[key].append(item)
        if isinstance(context.get("context"), dict):
            merged["context"].update(context["context"])
    if not any(merged[key] for key in ("available_tools", "selected_tools", "available_tool_details", "selected_tool_details")) and not merged["context"]:
        return None
    return merged
