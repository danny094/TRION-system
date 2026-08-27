import subprocess
import sys
from dataclasses import fields
from types import SimpleNamespace
from typing import get_type_hints

import pytest

from mcp import client, client_handoff, hub as hub_module
from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)
from tools.contracts import ToolCall, ToolResult
from tools.executor import run_tool


class _Hub:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


def test_importing_client_does_not_load_hub_in_fresh_process():
    probe = "import sys; import mcp.client; assert 'mcp.hub' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_client_handoff_annotations_are_runtime_resolvable():
    hints = get_type_hints(client_handoff.call_tool_result)
    assert "arguments" in hints
    assert hints["return"] is MCPToolResultEnvelope


def _envelopes():
    return (
        MCPToolResultEnvelope(ToolStatus.SUCCESS),
        MCPToolResultEnvelope(
            ToolStatus.SUCCESS,
            content_presence=Presence.EMPTY,
            content=[],
            structured_content_presence=Presence.EMPTY,
            structured_content={},
        ),
        MCPToolResultEnvelope(
            ToolStatus.SUCCESS,
            content_presence=Presence.VALUE,
            content=[{"type": "text", "text": "ok"}],
            structured_content_presence=Presence.VALUE,
            structured_content={"value": 1},
        ),
        MCPToolResultEnvelope(
            ToolStatus.TOOL_FAILURE,
            is_error_presence=Presence.VALUE,
            is_error=True,
        ),
        MCPToolResultEnvelope(
            ToolStatus.PROTOCOL_FAILURE,
            protocol_error={"code": -1, "message": "bad response"},
        ),
        MCPToolResultEnvelope(
            ToolStatus.TRANSPORT_FAILURE,
            transport_diagnostic="offline",
        ),
    )


@pytest.mark.parametrize("envelope", _envelopes())
def test_client_handoff_preserves_typed_envelope_identity(monkeypatch, envelope):
    hub = _Hub(envelope)
    monkeypatch.setattr(client_handoff, "get_hub", lambda: hub)
    assert client_handoff.call_tool_result("demo", {"x": 2}) is envelope
    assert hub.calls == [("demo", {"x": 2})]


@pytest.mark.parametrize("envelope", _envelopes())
def test_hub_preserves_transport_envelope_identity(monkeypatch, envelope):
    hub = hub_module.MCPHub()
    monkeypatch.setattr(hub, "initialize", lambda: None)
    monkeypatch.setattr(
        hub_module,
        "acquire_route",
        lambda _name: SimpleNamespace(mcp_name="demo"),
    )
    monkeypatch.setattr(
        hub_module,
        "dispatch_acquired_route",
        lambda _token, _arguments: envelope,
    )
    assert hub.call_tool("demo", {}) is envelope


def test_client_facade_delegates_without_changing_arguments(monkeypatch):
    marker = {"result": {"ok": True}}
    seen = []

    def fake_call_tool_result(name, arguments, timeout):
        seen.append((name, arguments, timeout))
        return marker

    monkeypatch.setattr(client.client_handoff, "call_tool_result", fake_call_tool_result)
    assert client.call_tool("demo", {"x": 1}, timeout=2.5) is marker
    assert seen == [("demo", {"x": 1}, 2.5)]


def test_tool_result_has_no_second_status_or_payload_authority():
    assert [field.name for field in fields(ToolResult)] == [
        "tool_name", "step_id", "envelope", "duration_s"
    ]


def test_tools_executor_rejects_noncanonical_client_result():
    result = run_tool(ToolCall("demo"), lambda *_args: {"result": {}})

    assert result.envelope.status is ToolStatus.PROTOCOL_FAILURE
    assert result.envelope.protocol_error == {
        "code": -32603,
        "message": "non-canonical tool result",
    }
