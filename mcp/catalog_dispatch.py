"""Dispatch calls through an acquired MCP catalog token."""

from typing import Any

from mcp.catalog_contracts import MCPCallToken


def dispatch_acquired_route(token: MCPCallToken, arguments: dict[str, Any]) -> Any:
    try:
        return token.transport.call_tool(token.tool_name, arguments)
    finally:
        token.lease.release()
