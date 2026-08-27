"""Single P13 projection from request outcome to typed tools/list result."""

from collections.abc import Mapping

from mcp.protocol_contracts import (
    MCPToolsListProtocolResult,
    MCPToolsListProtocolStatus as ListStatus,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)


def project_tools_list_response(outcome: MCPTransportRequestOutcome) -> MCPToolsListProtocolResult:
    if not isinstance(outcome, MCPTransportRequestOutcome):
        raise TypeError("tools/list projection requires MCPTransportRequestOutcome")
    if outcome.status is RequestStatus.PROTOCOL_FAILURE:
        return MCPToolsListProtocolResult(ListStatus.PROTOCOL_FAILURE)
    if outcome.status is RequestStatus.TRANSPORT_FAILURE:
        return MCPToolsListProtocolResult(ListStatus.TRANSPORT_FAILURE)
    payload = outcome.payload
    if isinstance(payload, Mapping) and "tools" in payload:
        tools = payload["tools"]
    elif isinstance(payload, (list, tuple)):
        tools = payload
    else:
        return MCPToolsListProtocolResult(ListStatus.PROTOCOL_FAILURE)
    if not isinstance(tools, (list, tuple)) or not all(isinstance(tool, Mapping) for tool in tools):
        return MCPToolsListProtocolResult(ListStatus.PROTOCOL_FAILURE)
    if not tools:
        return MCPToolsListProtocolResult(ListStatus.SUCCESS_EMPTY)
    return MCPToolsListProtocolResult(ListStatus.SUCCESS_WITH_TOOLS, tuple(tools))
