import pytest

from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)
from plugins import bridge


def _success(presence: Presence) -> MCPToolResultEnvelope:
    if presence is Presence.MISSING:
        return MCPToolResultEnvelope(ToolStatus.SUCCESS)
    if presence is Presence.EMPTY:
        return MCPToolResultEnvelope(
            ToolStatus.SUCCESS,
            structured_content_presence=Presence.EMPTY,
            structured_content={},
        )
    return MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=Presence.VALUE,
        structured_content={"value": "kept"},
    )


def _failure(status: ToolStatus) -> MCPToolResultEnvelope:
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
def test_permitted_tool_preserves_success_presence(monkeypatch, presence):
    envelope = _success(presence)
    monkeypatch.setattr(bridge, "is_tool_allowed", lambda _manifest, _tool: True)
    monkeypatch.setattr(bridge, "call_tool", lambda *_args, **_kwargs: envelope)

    result = bridge.call_permitted_tool({"id": "demo"}, "sample", {"x": 1})

    assert result is envelope
    assert result.structured_content_presence is presence


@pytest.mark.parametrize(
    "status",
    [
        ToolStatus.TOOL_FAILURE,
        ToolStatus.PROTOCOL_FAILURE,
        ToolStatus.TRANSPORT_FAILURE,
    ],
)
def test_permitted_tool_preserves_failure_status(monkeypatch, status):
    envelope = _failure(status)
    monkeypatch.setattr(bridge, "is_tool_allowed", lambda _manifest, _tool: True)
    monkeypatch.setattr(bridge, "call_tool", lambda *_args, **_kwargs: envelope)

    result = bridge.call_permitted_tool({"id": "demo"}, "sample", {})

    assert result is envelope
    assert result.status is status


def test_permission_denial_does_not_call_tool(monkeypatch):
    called = False

    def unexpected_call(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(bridge, "is_tool_allowed", lambda _manifest, _tool: False)
    monkeypatch.setattr(bridge, "call_tool", unexpected_call)

    with pytest.raises(PermissionError):
        bridge.call_permitted_tool({"id": "demo"}, "sample", {})

    assert called is False
