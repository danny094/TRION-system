import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)


ADMIN_API_DIR = Path(__file__).resolve().parents[1] / "adapters" / "admin-api"


def _load_graph_sync():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    module = importlib.import_module("commander_blueprint_graph_sync")
    return importlib.reload(module)


def _blueprint():
    return SimpleNamespace(
        id="demo-blueprint",
        name="Demo",
        description="Demo blueprint",
        tags=["sample"],
        network=None,
        image=None,
        resources=None,
        updated_at=None,
    )


def _success(presence: Presence, structured=None):
    if presence is Presence.MISSING:
        return MCPToolResultEnvelope(ToolStatus.SUCCESS)
    return MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=presence,
        structured_content={} if presence is Presence.EMPTY else structured,
    )


def _failure(status: ToolStatus):
    if status is ToolStatus.TOOL_FAILURE:
        return MCPToolResultEnvelope(
            status,
            is_error_presence=Presence.VALUE,
            is_error=True,
        )
    if status is ToolStatus.PROTOCOL_FAILURE:
        return MCPToolResultEnvelope(status, protocol_error={"code": -32600})
    return MCPToolResultEnvelope(status, transport_diagnostic="offline")


@pytest.mark.parametrize("presence", list(Presence))
def test_sync_preserves_search_presence(monkeypatch, presence):
    graph_sync = _load_graph_sync()
    calls = []
    existing = {
        "results": [
            {"metadata": json.dumps({"blueprint_id": "demo-blueprint"})}
        ]
    }

    def call_tool(name, _arguments):
        calls.append(name)
        if name == "memory_graph_search":
            payload = existing if presence is Presence.VALUE else None
            return _success(presence, payload)
        return _success(Presence.MISSING)

    monkeypatch.setattr("mcp.client.call_tool", call_tool)
    monkeypatch.setattr(graph_sync, "ensure_store_initialized", lambda: None)

    assert graph_sync.sync_blueprint_to_graph(_blueprint(), "trusted") is True
    expected = ["memory_graph_search"] if presence is Presence.VALUE else [
        "memory_graph_search",
        "graph_add_node",
    ]
    assert calls == expected


@pytest.mark.parametrize(
    "status",
    [
        ToolStatus.TOOL_FAILURE,
        ToolStatus.PROTOCOL_FAILURE,
        ToolStatus.TRANSPORT_FAILURE,
    ],
)
def test_search_failure_does_not_write(monkeypatch, status):
    graph_sync = _load_graph_sync()
    calls = []

    def call_tool(name, _arguments):
        calls.append(name)
        return _failure(status)

    monkeypatch.setattr("mcp.client.call_tool", call_tool)
    monkeypatch.setattr(graph_sync, "ensure_store_initialized", lambda: None)

    assert graph_sync.sync_blueprint_to_graph(_blueprint(), "trusted") is False
    assert calls == ["memory_graph_search"]


@pytest.mark.parametrize(
    "write_result, expected_count",
    [
        (_success(Presence.MISSING), 1),
        (_success(Presence.EMPTY), 1),
        (_success(Presence.VALUE, {"node_id": "n1"}), 1),
        (_failure(ToolStatus.TOOL_FAILURE), 0),
        (_failure(ToolStatus.PROTOCOL_FAILURE), 0),
        (_failure(ToolStatus.TRANSPORT_FAILURE), 0),
    ],
)
def test_bulk_sync_counts_only_success(monkeypatch, write_result, expected_count):
    graph_sync = _load_graph_sync()

    def call_tool(name, _arguments):
        if name == "memory_graph_search":
            return _success(Presence.EMPTY)
        return write_result

    monkeypatch.setattr("mcp.client.call_tool", call_tool)
    monkeypatch.setattr(graph_sync, "ensure_store_initialized", lambda: None)
    monkeypatch.setattr(graph_sync, "list_blueprints", lambda: [_blueprint()])

    assert graph_sync.sync_blueprints_to_graph() == expected_count


@pytest.mark.parametrize(
    "write_result, expected_count",
    [
        (_success(Presence.MISSING), 1),
        (_success(Presence.EMPTY), 1),
        (_success(Presence.VALUE, {"node_id": "n1"}), 1),
        (_failure(ToolStatus.TOOL_FAILURE), 0),
        (_failure(ToolStatus.PROTOCOL_FAILURE), 0),
        (_failure(ToolStatus.TRANSPORT_FAILURE), 0),
    ],
)
def test_remove_counts_only_successful_mark_writes(
    monkeypatch,
    write_result,
    expected_count,
):
    graph_sync = _load_graph_sync()

    def call_tool(name, _arguments):
        if name == "memory_graph_search":
            return _success(Presence.VALUE, {
                "results": [{
                    "id": "node-1",
                    "metadata": json.dumps({"blueprint_id": "demo-blueprint"}),
                }],
            })
        return write_result

    monkeypatch.setattr("mcp.client.call_tool", call_tool)
    monkeypatch.setattr(graph_sync, "ensure_store_initialized", lambda: None)

    assert graph_sync.remove_blueprint_from_graph("demo-blueprint") == expected_count
