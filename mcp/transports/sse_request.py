"""Request builders for the standalone SSE transport."""

from collections.abc import Mapping
from typing import Any, Dict, Optional

import requests

from mcp.protocol_negotiation_contracts import (
    SUPPORTED_MCP_PROTOCOL_VERSION,
    MCPProtocolNegotiationResult,
    MCPProtocolNegotiationStatus as NegotiationStatus,
    validate_protocol_version,
)


def build_sse_initialize_payload() -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mcp-hub", "version": "1.0.0"},
        },
    }

def build_sse_tools_list_payload() -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}


def build_sse_tool_call_payload(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def build_sse_headers(
    api_key: Optional[str] = None,
    accept_event_stream: bool = False,
    protocol_negotiation_result: MCPProtocolNegotiationResult | None = None,
) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if accept_event_stream:
        headers["Accept"] = "text/event-stream"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if (
        protocol_negotiation_result is not None
        and protocol_negotiation_result.status is NegotiationStatus.NEGOTIATED
    ):
        headers["MCP-Protocol-Version"] = protocol_negotiation_result.protocol_version
    return headers


def initialize_sse_protocol(transport) -> MCPProtocolNegotiationResult:
    response = requests.post(
        transport.url,
        json=build_sse_initialize_payload(),
        headers=build_sse_headers(transport.api_key),
        timeout=transport.timeout,
    )
    response.raise_for_status()
    try:
        data = response.json()
    except Exception:
        return validate_protocol_version({})
    result = data.get("result") if isinstance(data, Mapping) else None
    protocol_value = result.get("protocolVersion") if isinstance(result, Mapping) else {}
    return validate_protocol_version(protocol_value)
