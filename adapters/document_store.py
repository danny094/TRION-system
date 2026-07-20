from typing import Any

from mcp.client import call_tool


def workspace_save_document_chunk(
    conversation_id: str,
    content: str,
    entry_type: str,
    source_layer: str,
) -> int:
    result = call_tool(
        "workspace_save",
        {
            "conversation_id": conversation_id,
            "content": content,
            "entry_type": entry_type,
            "source_layer": source_layer,
        },
    )
    entry_id = _read_workspace_entry_id(result)
    if entry_id <= 0:
        raise ValueError("workspace_save_missing_id")
    return entry_id


def semantic_save_document_chunk(
    conversation_id: str,
    content: str,
    content_type: str,
    key: str | None,
    value: str | None,
) -> dict[str, object]:
    result = call_tool(
        "memory_semantic_save",
        {
            "conversation_id": conversation_id,
            "content": content,
            "content_type": content_type,
            "key": key,
            "value": value,
        },
    )
    payload = _unwrap_result(result)
    if not _is_success(payload):
        raise ValueError("memory_semantic_save_failed")
    return payload if isinstance(payload, dict) else {"result": payload}


def _read_workspace_entry_id(result: Any) -> int:
    payload = _unwrap_result(result)
    if not isinstance(payload, dict):
        return 0
    structured = payload.get("structuredContent")
    if isinstance(structured, dict):
        return int(structured.get("id") or 0)
    return int(payload.get("id") or 0)


def _unwrap_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    if result.get("error"):
        return {}
    payload = result.get("result", result)
    if isinstance(payload, dict) and payload.get("error"):
        return {}
    return payload


def _is_success(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("success") is True:
        return True
    structured = payload.get("structuredContent")
    return isinstance(structured, dict) and structured.get("success") is True
