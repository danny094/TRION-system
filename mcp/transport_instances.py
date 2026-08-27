"""Bind desired MCP entries to concrete transport instances."""

from collections.abc import Mapping
from typing import Any

from mcp.catalog_contracts import MCPTransportBindingOutcome, MCPTransportBindingStatus
from mcp.transports import HTTPTransport, SSETransport, STDIOTransport


def bind_transport_instance(mcp_name: str, config: Mapping[str, Any]) -> MCPTransportBindingOutcome:
    if not bool(config.get("enabled", False)):
        return MCPTransportBindingOutcome(MCPTransportBindingStatus.DISABLED)
    transport_type = str(config.get("transport", "http")).strip().lower()
    try:
        if transport_type in {"http", "https"}:
            transport = HTTPTransport(config.get("url", ""), config.get("api_key", ""))
        elif transport_type == "sse":
            transport = SSETransport(config.get("url", ""), config.get("api_key", ""))
        elif transport_type == "stdio":
            transport = STDIOTransport(config.get("command", ""), cwd=config.get("cwd", ""))
        else:
            return MCPTransportBindingOutcome(MCPTransportBindingStatus.MISSING)
    except Exception as exc:
        return MCPTransportBindingOutcome(
            MCPTransportBindingStatus.CONSTRUCTION_FAILED,
            diagnostic=str(exc) or f"{mcp_name}_transport_construction_failed",
        )
    return MCPTransportBindingOutcome(MCPTransportBindingStatus.BOUND, transport=transport)
