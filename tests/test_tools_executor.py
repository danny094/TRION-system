from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)
from tools.contracts import ToolCall
from tools.executor import run_tool


def _value_envelope() -> MCPToolResultEnvelope:
    return MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=Presence.VALUE,
        structured_content={"ok": True, "value": 42},
    )


def test_run_tool_preserves_mcp_envelope_identity():
    seen = {}
    envelope = _value_envelope()

    def fake_call_tool(name, arguments, timeout):
        seen.update(name=name, arguments=arguments, timeout=timeout)
        return envelope

    result = run_tool(
        ToolCall("demo_tool", {"x": 1}, "step-1", 2.5),
        call_tool_fn=fake_call_tool,
    )

    assert result.envelope is envelope
    assert result.tool_name == "demo_tool"
    assert result.step_id == "step-1"
    assert result.duration_s >= 0
    assert seen == {"name": "demo_tool", "arguments": {"x": 1}, "timeout": 2.5}


def test_run_tool_preserves_missing_empty_and_value_envelopes():
    envelopes = (
        MCPToolResultEnvelope(ToolStatus.SUCCESS),
        MCPToolResultEnvelope(
            ToolStatus.SUCCESS,
            structured_content_presence=Presence.EMPTY,
            structured_content={},
        ),
        _value_envelope(),
    )

    for envelope in envelopes:
        result = run_tool(ToolCall("demo"), lambda *_args: envelope)
        assert result.envelope is envelope


def test_run_tool_preserves_typed_tool_failure():
    envelope = MCPToolResultEnvelope(
        ToolStatus.TOOL_FAILURE,
        structured_content_presence=Presence.VALUE,
        structured_content={"details": "bad"},
        is_error_presence=Presence.VALUE,
        is_error=True,
    )

    result = run_tool(ToolCall("missing", step_id="step-2"), lambda *_args: envelope)

    assert result.envelope is envelope
    assert result.envelope.status is ToolStatus.TOOL_FAILURE


def test_run_tool_maps_call_exception_to_transport_failure():
    def fake_call_tool(*_args):
        raise RuntimeError("transport failed")

    result = run_tool(ToolCall("unstable", step_id="step-3"), fake_call_tool)

    assert result.envelope.status is ToolStatus.TRANSPORT_FAILURE
    assert result.envelope.transport_diagnostic == "transport failed"


def test_run_tool_rejects_missing_tool_name_without_calling_mcp():
    def fail_call_tool(*_args):
        raise AssertionError("MCP must not be called without tool name")

    result = run_tool(ToolCall("", step_id="step-4"), fail_call_tool)

    assert result.envelope.status is ToolStatus.PROTOCOL_FAILURE
    assert result.envelope.protocol_error == {
        "code": -32602,
        "message": "missing_tool_name",
    }
