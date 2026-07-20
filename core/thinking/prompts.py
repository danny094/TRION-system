import json
from typing import Any, Iterable, Mapping

from config import get_thinking_context_char_cap, get_thinking_context_item_cap
from core.input_processor.contracts import DocumentContext
from intelligence_modules.prompt_manager import load_prompt


def build_thinking_prompt(
    user_text: str,
    *,
    available_tools: Iterable[Any] | None = None,
    context_summary: str = "",
    document_context_summary: str = "",
    replan_context: Mapping[str, Any] | None = None,
) -> str:
    parts = [load_prompt("layers", "thinking")]
    tools_json = _tools_json(available_tools)
    if tools_json:
        parts.append(load_prompt("layers", "thinking_available_tools", tools_json=tools_json))
    if context_summary:
        parts.append(load_prompt("layers", "thinking_context_summary", context_summary=context_summary))
    if document_context_summary:
        parts.append(
            load_prompt(
                "layers",
                "thinking_document_context",
                document_context_summary=document_context_summary,
            )
        )
    if replan_context:
        parts.append(
            load_prompt(
                "layers",
                "thinking_replan_context",
                failed_step_id=str(replan_context.get("failed_step_id") or ""),
                failure_status=str(replan_context.get("failure_status") or ""),
                failure_error=str(replan_context.get("failure_error") or ""),
                replan_count=str(replan_context.get("replan_count") or "0"),
                artifacts_json=_json_text(replan_context.get("artifacts") or []),
            )
        )
    parts.append(load_prompt("layers", "thinking_user_request", user_text=str(user_text or "").strip()))
    return "\n\n".join(part for part in parts if part.strip())


def reduce_document_context(document_context: DocumentContext | None) -> str:
    if not document_context:
        return ""
    summary = {
        "summary": str(document_context.summary or "")[:500],
        "key_facts": [str(item)[:160] for item in list(document_context.key_facts or [])[:4]],
        "total_chunks": int(document_context.total_chunks or 0),
        "workspace_entry_ids": list(document_context.workspace_entry_ids or [])[:6],
        "preferred_entry_ids": list(document_context.preferred_entry_ids or [])[:6],
        "index_like_entry_ids": list(document_context.index_like_entry_ids or [])[:6],
        "chapter_candidate_entry_ids": list(document_context.chapter_candidate_entry_ids or [])[:6],
        "semantic_keys": [str(item)[:80] for item in list(document_context.semantic_keys or [])[:6]],
        "semantic_candidate_keys": [str(item)[:80] for item in list(document_context.semantic_candidate_keys or [])[:6]],
        "original_char_count": int(document_context.original_char_count or 0),
    }
    return _json_text(summary)


def reduce_orchestrator_context(
    context: Mapping[str, Any] | None,
    *,
    item_cap: int | None = None,
    char_cap: int | None = None,
) -> str:
    if not isinstance(context, Mapping):
        return ""
    item_limit = max(1, int(item_cap if item_cap is not None else get_thinking_context_item_cap()))
    char_limit = max(120, int(char_cap if char_cap is not None else get_thinking_context_char_cap()))
    summary = {}
    for key in ("conversation_policy", "context_scope_filter", "memory", "workspace", "active_containers", "runtime"):
        value = _summarize_context_value(context.get(key), item_limit)
        if value not in ({}, [], "", None):
            summary[key] = value
    text = _json_text(summary)
    return text if len(text) <= char_limit else f"{text[: max(0, char_limit - 16)].rstrip()}...(truncated)"


def _tools_json(available_tools: Iterable[Any] | None) -> str:
    # Prompt-Provenance (Doc 36 Regel 5):
    # Felder kommen aus tool_intents.json via adapters/tool_runner_bridge._tool_intent_for(),
    # werden zu ToolDescriptor-Attributen durch
    # core/orchestrator/tool_descriptor_projection.descriptor_from_raw()
    # und in orchestrator_stage.py in available_tool_details / selected_tool_details übertragen.
    # tool_role / capability_risk / capability_operation / capability_required_args
    # werden nur für Nicht-String-Tools serialisiert (ToolDescriptor oder Mapping mit diesen Keys).
    items = []
    for tool in available_tools or []:
        if isinstance(tool, Mapping):
            entry: dict = {
                "name": str(tool.get("name") or ""),
                "description": str(tool.get("description") or ""),
                "mcp": str(tool.get("mcp") or ""),
            }
            cap_ev = list(tool.get("capability_evidence_types") or [])
            if cap_ev:
                entry["capability_evidence_types"] = cap_ev
            _inject_tool_metadata(entry, tool.get, key_fn=lambda k: k)
            items.append(entry)
        elif isinstance(tool, str):
            # Plain-String-Fallback (z. B. available_tools als Namen-Liste)
            items.append({"name": tool, "description": "", "mcp": ""})
        else:
            name = str(getattr(tool, "name", "") or "")
            description = str(getattr(tool, "description", "") or "")
            mcp = str(getattr(tool, "mcp", "") or "")
            entry = {"name": name, "description": description, "mcp": mcp}
            cap_ev = list(getattr(tool, "capability_evidence_types", None) or [])
            if cap_ev:
                entry["capability_evidence_types"] = cap_ev
            _inject_tool_metadata(entry, lambda k: getattr(tool, k, None))
            items.append(entry)
    return _json_text(items) if items else ""


def _inject_tool_metadata(entry: dict, get_fn: Any, key_fn: Any = None) -> None:
    """Inject tool_role, capability_risk, capability_operation, capability_required_args.

    Provenance: values originate from tool_intents.json loaded by tool_runner_bridge.
    Only non-empty values are written to keep prompt size minimal.
    """
    for field in ("tool_role", "capability_risk", "capability_operation"):
        val = str(get_fn(field) or "")
        if val:
            entry[field] = val
    req_args = list(get_fn("capability_required_args") or [])
    if req_args:
        entry["capability_required_args"] = req_args


def _summarize_context_value(value: Any, item_cap: int) -> Any:
    if isinstance(value, Mapping):
        if value.get("available") is False:
            return _filter_mapping(value, ("available", "skipped", "reason", "error", "namespace"))
        for list_key in ("items", "entries", "results"):
            if isinstance(value.get(list_key), list):
                return {
                    "available": bool(value.get("available", True)),
                    list_key: [_normalize_item(item) for item in value.get(list_key, [])[:item_cap]],
                    "count": len(value.get(list_key, [])),
                }
        return {str(key): _normalize_item(item) for key, item in value.items() if str(key) in {"memory_mode", "allow_global_memory_read", "allow_long_term_write", "allowed_namespaces", "enabled", "active"}}
    if isinstance(value, list):
        return [_normalize_item(item) for item in value[:item_cap]]
    return _normalize_item(value)


def _normalize_item(item: Any) -> Any:
    if isinstance(item, Mapping):
        data = {}
        for index, (key, value) in enumerate(item.items()):
            if index >= 6:
                break
            data[str(key)] = _normalize_item(value)
        return data
    if isinstance(item, list):
        return [_normalize_item(value) for value in item[:3]]
    if isinstance(item, str):
        return item[:160]
    return item


def _filter_mapping(value: Mapping[str, Any], keys: Iterable[str]) -> Mapping[str, Any]:
    return {key: value.get(key) for key in keys if key in value}


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)
