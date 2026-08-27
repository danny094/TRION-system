import re
from typing import Any, Mapping

from utils.time_followups import parse_time_followup_offset_seconds

_TIME_TOKENS = ("wie viel uhr", "wie spät", "wie spaet", "uhrzeit", "aktuelle zeit", "utc")
_FILE_TOKENS = ("/trion-home/", ".txt", "datei", "file", "lies", "lese", "lesen")
_CAPABILITY_HINTS = {
    "time_current": ("time", "clock", "utc", "zeit", "uhr", "datum"),
    "file_read": ("file", "read", "datei", "lesen", "lies", "lese", "workspace", "document", "entry", "content", "path", "txt", "get"),
}


def parse_response_projection(user_text: str) -> str:
    text = _normalize(user_text)
    if "utc iso" in text or "als utc iso" in text or "nur utc iso" in text:
        return "utc_iso"
    if any(token in text for token in ("nur das datum", "nur datum", "only date")):
        return "date_only"
    if any(token in text for token in ("nur die zeit", "nur zeit", "only time")):
        return "time_only"
    return ""


def parse_response_derivation(user_text: str) -> dict[str, Any]:
    seconds = parse_time_followup_offset_seconds(user_text)
    if seconds is None:
        return {}
    return {"kind": "time_offset", "seconds": int(seconds)}


def infer_required_tools(user_text: str, available_tools: list[str], selected_tools: list[str]) -> list[str]:
    return infer_required_tools_with_completed(user_text, available_tools, selected_tools, completed_tools=[])


def infer_required_tools_with_completed(
    user_text: str,
    available_tools: list[Any],
    selected_tools: list[str],
    *,
    completed_tools: list[str],
) -> list[str]:
    required: list[str] = []
    text = _normalize(user_text)
    completed = {str(item).strip() for item in completed_tools if str(item).strip()}
    if _contains_any(text, _TIME_TOKENS):
        time_tools = _capability_candidates("time_current", available_tools)
        if time_tools:
            time_tool = time_tools[0]
            if time_tool not in completed:
                required.append(time_tool)
    if _contains_any(text, _FILE_TOKENS):
        file_tools = _capability_candidates("file_read", available_tools)
        if file_tools:
            file_tool = file_tools[0]
            if file_tool not in completed:
                required.append(file_tool)
    ordered = list(selected_tools)
    for tool in required:
        if tool not in ordered:
            ordered.append(tool)
    return ordered


def detect_additional_evidence_need(
    user_text: str,
    available_tools: list[Any],
    selected_tools: list[str],
    *,
    completed_tools: list[str] | None = None,
) -> dict[str, Any]:
    text = _normalize(user_text)
    completed = {str(item).strip() for item in completed_tools or [] if str(item).strip()}
    file_requested = _contains_any(text, _FILE_TOKENS)
    time_requested = _contains_any(text, _TIME_TOKENS)
    file_candidates = _capability_candidates("file_read", available_tools)
    if file_requested and not any(tool in set(selected_tools) | completed for tool in file_candidates):
        return {
            "kind": "file_read",
            "reason": "The request also asks for verified file content, but no file-read tool is selected.",
            "candidate_tools": file_candidates,
        }
    time_candidates = _capability_candidates("time_current", available_tools)
    if time_requested and not any(tool in set(selected_tools) | completed for tool in time_candidates):
        return {
            "kind": "time_current",
            "reason": "The request still needs verified current time evidence from the time tool.",
            "candidate_tools": time_candidates,
        }
    return {}


def completed_tool_names(artifacts: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for artifact in artifacts or []:
        if not isinstance(artifact, Mapping):
            continue
        if str(artifact.get("artifact_type") or "").strip() != "tool_result":
            continue
        name = str(artifact.get("tool") or artifact.get("tool_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def unresolved_additional_evidence_tools(plan: Any, artifacts: list[dict[str, Any]] | None) -> list[str]:
    need = getattr(plan, "additional_evidence_need", None)
    candidate_tools = [str(item).strip() for item in getattr(need, "candidate_tools", []) or [] if str(item).strip()]
    if not candidate_tools:
        return []
    completed = set(completed_tool_names(artifacts))
    return [tool for tool in candidate_tools if tool not in completed]


def _capability_candidates(capability_kind: str, available_tools: list[Any]) -> list[str]:
    hints = _CAPABILITY_HINTS.get(capability_kind, ())
    if not hints:
        return []
    names: list[str] = []
    for tool in available_tools or []:
        name = str(tool.get("name") if isinstance(tool, Mapping) else tool).strip()
        if not name or name in names:
            continue
        haystack = _tool_haystack(tool)
        score = sum(1 for token in hints if token in haystack)
        if score >= 2 or (capability_kind == "time_current" and score >= 1):
            names.append(name)
    return names


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _tool_haystack(tool: Any) -> str:
    if isinstance(tool, Mapping):
        keywords = tool.get("intent_keywords")
        values = [
            tool.get("name"),
            tool.get("description"),
            tool.get("source"),
            tool.get("intent_description"),
            " ".join(str(item).strip() for item in keywords if str(item).strip()) if isinstance(keywords, list) else "",
        ]
        return _normalize(" ".join(str(value or "").replace("_", " ") for value in values))
    return _normalize(str(tool or "").replace("_", " "))


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())
