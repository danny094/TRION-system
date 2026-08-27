from time import monotonic
from typing import Any, Callable, Dict

from mcp.client import call_tool
from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope
from tools.contracts import ToolCall, ToolResult

CallToolFn = Callable[[str, Dict[str, Any], float], MCPToolResultEnvelope]


def run_tool(tool_call: ToolCall, call_tool_fn: CallToolFn = call_tool) -> ToolResult:
    started = monotonic()
    tool_name = str(tool_call.tool_name or "").strip()

    if not tool_name:
        return ToolResult(
            tool_name=tool_name,
            step_id=tool_call.step_id,
            envelope=MCPToolResultEnvelope(
                MCPToolCallStatus.PROTOCOL_FAILURE,
                protocol_error={"code": -32602, "message": "missing_tool_name"},
            ),
            duration_s=monotonic() - started,
        )

    try:
        raw = call_tool_fn(
            tool_name,
            dict(tool_call.arguments or {}),
            max(0.2, float(tool_call.timeout_s or 0.0)),
        )
    except Exception as exc:
        return ToolResult(
            tool_name=tool_name,
            step_id=tool_call.step_id,
            envelope=MCPToolResultEnvelope(
                MCPToolCallStatus.TRANSPORT_FAILURE,
                transport_diagnostic=str(exc) or "tool execution transport failure",
            ),
            duration_s=monotonic() - started,
        )

    if not isinstance(raw, MCPToolResultEnvelope):
        raw = MCPToolResultEnvelope(
            MCPToolCallStatus.PROTOCOL_FAILURE,
            protocol_error={"code": -32603, "message": "non-canonical tool result"},
        )
    return ToolResult(
        tool_name=tool_name,
        step_id=tool_call.step_id,
        envelope=raw,
        duration_s=monotonic() - started,
    )
