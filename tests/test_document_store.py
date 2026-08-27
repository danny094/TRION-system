from adapters import document_store
from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)


def test_workspace_save_document_chunk_reads_structured_entry_id(monkeypatch):
    def fake_call_tool(name, arguments, timeout=5.0):
        assert name == "workspace_save"
        assert arguments["entry_type"] == "document_chunk"
        return MCPToolResultEnvelope(
            MCPToolCallStatus.SUCCESS,
            structured_content_presence=MCPResultPresence.VALUE,
            structured_content={"id": 42},
        )

    monkeypatch.setattr(document_store, "call_tool", fake_call_tool)

    entry_id = document_store.workspace_save_document_chunk(
        "conv-1",
        "chunk content",
        "document_chunk",
        "input_processor",
    )

    assert entry_id == 42


def test_semantic_save_document_chunk_requires_success(monkeypatch):
    def fake_call_tool(name, arguments, timeout=5.0):
        assert name == "memory_semantic_save"
        assert arguments["content_type"] == "document_chunk"
        return MCPToolResultEnvelope(
            MCPToolCallStatus.SUCCESS,
            structured_content_presence=MCPResultPresence.VALUE,
            structured_content={"success": True, "id": "vec-1"},
        )

    monkeypatch.setattr(document_store, "call_tool", fake_call_tool)

    result = document_store.semantic_save_document_chunk(
        "conv-1",
        "chunk content",
        "document_chunk",
        "document_chunk_1",
        "chunk:1",
    )

    assert result["success"] is True
    assert result["id"] == "vec-1"
