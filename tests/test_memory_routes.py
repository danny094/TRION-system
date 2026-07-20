"""Memory-Routes Tests — gegen die existierenden SQL-Memory-MCP-Tools.

Diese Tests halten die Anti-Drift-Linie aus docs/34 und docs/36 Regel 2:
- Routes rufen Tools per Live-Discovery-Helper (``mcp.client.call_tool``)
- keine Routes-interne Tool-Listen, die nur Namen spiegeln
- der Anti-Drift-Test ``test_memory_routes_no_hardcoded_tool_list`` blockt
  Regressionen
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _resolve_admin_api_dir() -> Path:
    """Resolve the admin-api directory in both dev-repo and container layouts."""
    candidates = [
        ROOT / "adapters" / "admin-api",
        Path("/app"),
        ROOT,
    ]
    for path in candidates:
        if (path / "memory_routes.py").exists():
            return path
    raise FileNotFoundError("memory_routes.py not found in any known layout")


ADMIN_API_DIR = _resolve_admin_api_dir()


def _load_memory_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_memory_routes_for_test",
        ADMIN_API_DIR / "memory_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _json(response):
    import json as _json_lib

    return _json_lib.loads(response.body.decode("utf-8"))


def test_memory_recent_with_conversation_calls_memory_recent(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        captured["args"] = args
        return {"result": {"entries": [
            {"id": 1, "conversation_id": "conv-a", "content": "hello", "created_at": "2026-05-31T12:00:00Z"},
        ]}}

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
        return {"result": {"structuredContent": {"entries": []}}}

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)

    response = asyncio.run(memory_routes.memory_recent(conversation_id=None, limit=20))
    data = _json(response)

    assert captured["name"] == "memory_all_recent"
    assert data["count"] == 0


@pytest.mark.parametrize(
    "mode,expected_tool",
    [
        ("fts", "memory_search_fts"),
        ("semantic", "memory_semantic_search"),
        ("graph", "memory_graph_search"),
    ],
)
def test_memory_search_routes_each_mode_to_the_correct_tool(monkeypatch, mode, expected_tool):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        return {"result": {"results": [{"id": 1, "content": "x"}]}}

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
        return {"result": {"items": [{"conversation_id": "conv-a"}]}}

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
        return {"result": {"entries": [{"id": 7, "content": "drill"}]}}

    monkeypatch.setattr(memory_routes, "call_tool", fake_call_tool)

    response = asyncio.run(memory_routes.memory_conversation_drill_in(conversation_id="conv-a", limit=5))
    data = _json(response)

    assert captured["name"] == "memory_recent"
    assert captured["args"] == {"conversation_id": "conv-a", "limit": 5}
    assert data["conversation_id"] == "conv-a"
    assert data["count"] == 1


def test_policy_endpoint_derives_badge_from_meta(monkeypatch):
    memory_routes = _load_memory_routes()

    monkeypatch.setattr(
        memory_routes,
        "get_conversation_meta",
        lambda conv: {
            "memory": {"mode": "conversation_only", "do_not_remember": False},
            "status": {"temporary": False},
        },
    )

    response = asyncio.run(memory_routes.memory_conversation_policy(conversation_id="conv-a"))
    data = _json(response)

    assert data["memory_mode"] == "conversation_only"
    assert data["badge"] == "conversation_only"
    assert data["allow_global_memory_read"] is False
    assert data["allow_long_term_write"] is True


def test_policy_endpoint_returns_temporary_badge(monkeypatch):
    memory_routes = _load_memory_routes()

    monkeypatch.setattr(
        memory_routes,
        "get_conversation_meta",
        lambda conv: {
            "memory": {"mode": "global_enabled"},
            "status": {"temporary": True},
        },
    )

    response = asyncio.run(memory_routes.memory_conversation_policy(conversation_id="conv-tmp"))
    data = _json(response)

    assert data["badge"] == "temporary"
    assert data["temporary"] is True
    assert data["allow_long_term_write"] is False


def test_policy_endpoint_defaults_when_no_meta(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(memory_routes, "get_conversation_meta", lambda conv: None)
    monkeypatch.setattr(
        memory_routes,
        "build_default_conversation_meta",
        lambda conv: memory_routes.build_conversation_meta(
            {"conversation_id": conv, "memory": {"mode": "conversation_only"}},
            conv,
        ),
    )

    response = asyncio.run(memory_routes.memory_conversation_policy(conversation_id="conv-new"))
    data = _json(response)

    assert data["memory_mode"] == "conversation_only"
    assert data["badge"] == "conversation_only"
    assert data["allow_global_memory_read"] is False


def test_memory_delete_calls_memory_delete_with_int_id(monkeypatch):
    memory_routes = _load_memory_routes()
    captured = {}

    def fake_call_tool(name, args, timeout=5.0):
        captured["name"] = name
        captured["args"] = args
        return {"result": {"deleted": 1}}

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
        return {"result": {"deleted": 3}}

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


def test_mcp_error_propagates_as_503(monkeypatch):
    memory_routes = _load_memory_routes()

    def failing_call_tool(name, args, timeout=5.0):
        return {"error": "mcp_timeout:memory_recent:5s"}

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
