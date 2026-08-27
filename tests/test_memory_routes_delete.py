import asyncio

from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)
from tests.memory_routes_test_support import _json, _load_memory_routes


def _success(structured_content):
    return MCPToolResultEnvelope(
        MCPToolCallStatus.SUCCESS,
        structured_content_presence=MCPResultPresence.VALUE,
        structured_content=structured_content,
    )


def test_memory_delete_calls_memory_delete_with_int_id(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        captured["args"] = args
        return _success({"deleted": 1})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    response = asyncio.run(memory_routes.memory_delete(memory_id=42))
    data = _json(response)
    assert captured["name"] == "memory_delete"
    assert captured["args"] == {"id": 42}
    assert data["ok"] is True


def test_memory_delete_bulk_validates_and_calls(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        captured["args"] = args
        return _success({"deleted": 3})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    request = memory_routes.DeleteBulkRequest(ids=[1, 2, 3])
    response = asyncio.run(memory_routes.memory_delete_bulk(request))
    data = _json(response)
    assert captured["name"] == "memory_delete_bulk"
    assert captured["args"] == {"ids": [1, 2, 3]}
    assert data["deleted_count"] == 3


def test_memory_delete_bulk_rejects_empty(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(memory_routes, "call_tool", lambda *a, **kw: None)
    request = memory_routes.DeleteBulkRequest(ids=[])
    response = asyncio.run(memory_routes.memory_delete_bulk(request))
    assert response.status_code == 400
