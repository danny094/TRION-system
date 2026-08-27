"""Discover P13 tools/list outcomes for a complete desired MCP set."""

from collections.abc import Mapping
from typing import Any

from mcp.catalog_contracts import (
    MCPDesiredState,
    MCPDiscoveryOutcome,
    MCPDiscoveryStatus,
    MCPTransportBindingOutcome,
    MCPTransportBindingStatus,
)


def discover_catalog_outcomes(
    desired_state: MCPDesiredState,
    bindings_by_mcp: Mapping[str, MCPTransportBindingOutcome],
) -> Mapping[str, MCPDiscoveryOutcome]:
    outcomes: dict[str, MCPDiscoveryOutcome] = {}
    for mcp_name in desired_state.all_mcps:
        binding = bindings_by_mcp.get(mcp_name)
        if binding is None:
            outcomes[mcp_name] = MCPDiscoveryOutcome(MCPDiscoveryStatus.DISCOVERY_NOT_RUN)
        elif binding.status is MCPTransportBindingStatus.DISABLED:
            outcomes[mcp_name] = MCPDiscoveryOutcome(MCPDiscoveryStatus.DISABLED)
        elif binding.status is MCPTransportBindingStatus.CONSTRUCTION_FAILED:
            outcomes[mcp_name] = MCPDiscoveryOutcome(MCPDiscoveryStatus.TRANSPORT_BINDING_FAILED, diagnostic=binding.diagnostic)
        elif binding.status is MCPTransportBindingStatus.MISSING:
            outcomes[mcp_name] = MCPDiscoveryOutcome(MCPDiscoveryStatus.TRANSPORT_MISSING)
        else:
            outcomes[mcp_name] = _discover_bound(binding.transport)
    return outcomes


def _discover_bound(transport: Any) -> MCPDiscoveryOutcome:
    try:
        return MCPDiscoveryOutcome(
            MCPDiscoveryStatus.PROTOCOL_RESULT,
            protocol_result=transport.list_tools_protocol_result(),
        )
    except Exception as exc:
        return MCPDiscoveryOutcome(
            MCPDiscoveryStatus.TRANSPORT_BINDING_FAILED,
            diagnostic=str(exc) or "tools_list_failed",
        )
