"""Pure protocol projections for the MCP endpoint."""

from typing import Any, Dict

from mcp.protocol_negotiation_contracts import (
    SUPPORTED_MCP_PROTOCOL_VERSION,
    MCPProtocolNegotiationResult,
    validate_protocol_version,
)
from mcp.tool_result_contracts import (
    MCPToolCallStatus,
    MCPToolResultEnvelope,
    project_tool_result_wire_mapping,
)


def project_initialize_result(request_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION,
            "serverInfo": {"name": "trion-mcp-hub", "version": "1.0.0"},
            "capabilities": {"tools": {"listChanged": True}},
        },
    }


def validate_followup_protocol_version(value: object) -> MCPProtocolNegotiationResult:
    return validate_protocol_version(value)


def project_protocol_version_error(request_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32600, "message": "Invalid MCP protocol version"},
    }

def project_tools_call_response(
    request_id: Any,
    result: MCPToolResultEnvelope,
) -> Dict[str, Any]:
    if not isinstance(result, MCPToolResultEnvelope):
        raise TypeError("result must be MCPToolResultEnvelope")
    if result.status is MCPToolCallStatus.PROTOCOL_FAILURE:
        protocol_error = dict(result.protocol_error or {})
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": protocol_error.get("code", -32000),
                "message": protocol_error.get("message", "MCP protocol failure"),
            },
        }
    if result.status is MCPToolCallStatus.TRANSPORT_FAILURE:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": result.transport_diagnostic},
        }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": dict(project_tool_result_wire_mapping(result)),
    }
