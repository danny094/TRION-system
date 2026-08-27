from collections.abc import Mapping

from mcp.client import call_tool
from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope


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
    structured = _successful_structured(result, "workspace_save_failed")
    entry_id = int(structured.get("id") or 0)
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
    structured = _successful_structured(result, "memory_semantic_save_failed")
    return dict(structured)


def _successful_structured(
    result: MCPToolResultEnvelope,
    failure_code: str,
) -> Mapping[str, object]:
    if result.status is not MCPToolCallStatus.SUCCESS:
        raise ValueError(failure_code)
    if result.structured_content is None:
        raise ValueError(failure_code)
    return result.structured_content
