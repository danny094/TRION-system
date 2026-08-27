import asyncio
import ast

import pytest

from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)
from tests.memory_routes_test_support import ADMIN_API_DIR, _json, _load_memory_routes


def _success(structured_content):
    return MCPToolResultEnvelope(
        MCPToolCallStatus.SUCCESS,
        structured_content_presence=(
            MCPResultPresence.VALUE if structured_content else MCPResultPresence.EMPTY
        ),
        structured_content=structured_content,
    )


def test_memory_recent_with_conversation_calls_memory_recent(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        captured["args"] = args
        return _success({"entries": [
            {"id": 1, "conversation_id": "conv-a", "content": "hello", "created_at": "2026-05-31T12:00:00Z"},
        ]})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    response = asyncio.run(memory_routes.memory_recent(conversation_id="conv-a", limit=10))
    data = _json(response)
    assert captured["name"] == "memory_recent"
    assert captured["args"] == {"conversation_id": "conv-a", "limit": 10}
    assert data["count"] == 1
    assert data["entries"][0]["id"] == 1


def test_memory_recent_without_conversation_falls_back_to_all_recent(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        return _success({})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    response = asyncio.run(memory_routes.memory_recent(conversation_id=None, limit=20))
    data = _json(response)
    assert captured["name"] == "memory_all_recent"
    assert data["count"] == 0


@pytest.mark.parametrize(
    "mode,expected_tool",
    [("fts", "memory_search_fts"), ("semantic", "memory_semantic_search"), ("graph", "memory_graph_search")],
)
def test_memory_search_routes_each_mode_to_the_correct_tool(monkeypatch, mode, expected_tool):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        return _success({"results": [{"id": 1, "content": "x"}]})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    request = memory_routes.SearchRequest(query="foo", mode=mode)
    response = asyncio.run(memory_routes.memory_search(request))
    data = _json(response)
    assert captured["name"] == expected_tool
    assert data["mode"] == mode
    assert data["hits"][0]["source"] == mode


def test_memory_search_rejects_empty_query(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(memory_routes, "call_tool", lambda *a, **kw: None)
    request = memory_routes.SearchRequest(query="   ", mode="fts")
    response = asyncio.run(memory_routes.memory_search(request))
    assert response.status_code == 400


def test_memory_search_rejects_unknown_mode(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(memory_routes, "call_tool", lambda *a, **kw: None)
    request = memory_routes.SearchRequest(query="foo", mode="grep")
    response = asyncio.run(memory_routes.memory_search(request))
    assert response.status_code == 400


def test_memory_conversations_calls_list_conversations(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        return _success({"items": [{"conversation_id": "conv-a"}]})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    response = asyncio.run(memory_routes.memory_conversations(limit=10))
    data = _json(response)
    assert captured["name"] == "memory_list_conversations"
    assert data["count"] == 1


def test_memory_conversation_drill_in_uses_memory_recent(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        captured["args"] = args
        return _success({"entries": [{"id": 7, "content": "drill"}]})

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)
    response = asyncio.run(memory_routes.memory_conversation_drill_in(conversation_id="conv-a", limit=5))
    data = _json(response)
    assert captured["name"] == "memory_recent"
    assert captured["args"] == {"conversation_id": "conv-a", "limit": 5}
    assert data["conversation_id"] == "conv-a"
    assert data["count"] == 1


def test_mcp_error_propagates_as_503(monkeypatch):
    memory_routes = _load_memory_routes()

    def failing_call_tool(name, args, timeout=5.0):
        return MCPToolResultEnvelope(
            MCPToolCallStatus.TRANSPORT_FAILURE,
            transport_diagnostic="mcp_timeout:memory_recent:5s",
        )

    monkeypatch.setattr(memory_routes, "call_tool", failing_call_tool)
    response = asyncio.run(memory_routes.memory_recent(conversation_id="conv-a", limit=5))
    assert response.status_code == 503


def test_memory_routes_no_hardcoded_tool_list():
    """Anti-Drift gegen docs/36 Regel 2: keine hartcodierten Tool-Listen
    spiegeln, die nur Namen aus dem MCP-Layer wiederholen.

    Erlaubt: einzelne dedizierte ``call_tool('memory_recent', ...)``-Aufrufe.
    Verboten: Konstanten wie ``_MEMORY_TOOLS = [...]`` oder Sets, die nur
    Tool-Namen ohne Discovery-Quelle aufzaehlen.
    """
    source = (ADMIN_API_DIR / "memory_routes.py").read_text(encoding="utf-8")
    forbidden_patterns = [
        "_MEMORY_TOOLS",
        "ALLOWED_MEMORY_TOOLS",
        "KNOWN_MEMORY_TOOLS",
        "MEMORY_TOOL_LIST",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source, (
            f"Drift: '{pattern}' in memory_routes.py — "
            "Tool-Namen duerfen nur als einzelne call_tool-Argumente vorkommen, "
            "nicht als Liste/Konstante."
        )


def test_memory_route_contracts_retires_legacy_result_projectors():
    source = (ADMIN_API_DIR / "memory_route_contracts.py").read_text(encoding="utf-8")
    function_names = {
        node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)
    }
    assert function_names.isdisjoint({"_entries_from_result", "_mcp_error"})
