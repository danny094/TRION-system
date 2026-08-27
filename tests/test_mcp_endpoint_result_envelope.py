import asyncio
import inspect
import json

import pytest

from mcp import endpoint, endpoint_protocol
from mcp.protocol_negotiation_contracts import SUPPORTED_MCP_PROTOCOL_VERSION
from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)


def test_endpoint_initialize_projection_preserves_current_wire_value():
    source = inspect.getsource(endpoint_protocol)
    assert "protocol_negotiation_contracts" in source
    assert hasattr(endpoint_protocol, "validate_followup_protocol_version")
    assert endpoint_protocol.project_initialize_result("request-1") == {
        "jsonrpc": "2.0",
        "id": "request-1",
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "trion-mcp-hub", "version": "1.0.0"},
            "capabilities": {"tools": {"listChanged": True}},
        },
    }


@pytest.mark.parametrize(
    ("envelope", "wire_result"),
    [
        (MCPToolResultEnvelope(ToolStatus.SUCCESS), {}),
        (
            MCPToolResultEnvelope(
                ToolStatus.SUCCESS,
                content_presence=Presence.EMPTY,
                content=[],
                structured_content_presence=Presence.EMPTY,
                structured_content={},
                is_error_presence=Presence.VALUE,
                is_error=False,
            ),
            {"content": [], "structuredContent": {}, "isError": False},
        ),
        (
            MCPToolResultEnvelope(
                ToolStatus.SUCCESS,
                content_presence=Presence.VALUE,
                content=[{"type": "text", "text": "ok"}],
                structured_content_presence=Presence.VALUE,
                structured_content={"value": 2},
            ),
            {
                "content": [{"type": "text", "text": "ok"}],
                "structuredContent": {"value": 2},
            },
        ),
        (
            MCPToolResultEnvelope(
                ToolStatus.TOOL_FAILURE,
                content_presence=Presence.EMPTY,
                content=[],
                is_error_presence=Presence.VALUE,
                is_error=True,
            ),
            {"content": [], "isError": True},
        ),
    ],
)
def test_endpoint_tool_call_projects_canonical_wire_result(envelope, wire_result):
    assert endpoint_protocol.project_tools_call_response(1, envelope) == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": wire_result,
    }


@pytest.mark.parametrize(
    ("envelope", "wire_error"),
    [
        (
            MCPToolResultEnvelope(
                ToolStatus.PROTOCOL_FAILURE,
                protocol_error={"code": -32001, "message": "upstream"},
            ),
            {"code": -32001, "message": "upstream"},
        ),
        (
            MCPToolResultEnvelope(
                ToolStatus.TRANSPORT_FAILURE,
                transport_diagnostic="offline",
            ),
            {"code": -32000, "message": "offline"},
        ),
    ],
)
def test_endpoint_tool_call_projects_failure_from_typed_status(envelope, wire_error):
    assert endpoint_protocol.project_tools_call_response(2, envelope) == {
        "jsonrpc": "2.0",
        "id": 2,
        "error": wire_error,
    }


def test_endpoint_facade_exposes_only_the_extracted_projection_owner():
    assert endpoint.endpoint_protocol is endpoint_protocol
    assert not hasattr(endpoint, "_normalize_tool_result")


class _Request:
    def __init__(self, payload, protocol_version=None):
        self._payload = payload
        self.headers = {}
        if protocol_version is not None:
            self.headers["MCP-Protocol-Version"] = protocol_version

    async def json(self):
        return self._payload


@pytest.mark.parametrize("protocol_version", (None, "", 20241105, "2025-01-01"))
def test_endpoint_rejects_invalid_followup_version_before_hub(monkeypatch, protocol_version):
    hub_calls = []
    monkeypatch.setattr(endpoint, "get_hub", lambda: hub_calls.append(True))
    response = asyncio.run(endpoint.mcp_handler(_Request(
        {"jsonrpc": "2.0", "id": "request-2", "method": "tools/list"},
        protocol_version,
    )))
    assert response.status_code == 400
    assert json.loads(response.body)["error"]["code"] == -32600
    assert hub_calls == []


def test_endpoint_initialize_uses_canonical_version_without_hub(monkeypatch):
    monkeypatch.setattr(endpoint, "get_hub", lambda: pytest.fail("initialize must not access hub"))
    response = asyncio.run(endpoint.mcp_handler(_Request(
        {"jsonrpc": "2.0", "id": "request-3", "method": "initialize"}
    )))
    assert json.loads(response.body)["result"]["protocolVersion"] == SUPPORTED_MCP_PROTOCOL_VERSION


def test_endpoint_tools_call_preserves_empty_result_fields(monkeypatch):
    envelope = MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        content_presence=Presence.EMPTY,
        content=[],
        structured_content_presence=Presence.EMPTY,
        structured_content={},
    )

    class Hub:
        def call_tool(self, name, arguments):
            assert (name, arguments) == ("demo", {"x": 1})
            return envelope

    monkeypatch.setattr(endpoint, "get_hub", Hub)
    response = asyncio.run(endpoint.mcp_handler(_Request(
        {
            "jsonrpc": "2.0",
            "id": "request-4",
            "method": "tools/call",
            "params": {"name": "demo", "arguments": {"x": 1}},
        },
        SUPPORTED_MCP_PROTOCOL_VERSION,
    )))
    assert json.loads(response.body)["result"] == {
        "content": [],
        "structuredContent": {},
    }
