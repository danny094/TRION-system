"""Compose an unpublished MCP tool catalog candidate."""

from mcp.catalog_contracts import (
    MCPDiscoveryStatus,
    MCPToolCatalogSnapshot,
    MCPTransportBindingOutcome,
    MCPTransportBindingStatus,
    make_route,
)
from mcp.catalog_discovery import discover_catalog_outcomes
from mcp.config import get_mcp_desired_state
from mcp.protocol_contracts import MCPToolsListProtocolStatus
from mcp.transport_instances import bind_transport_instance


def build_catalog_snapshot() -> MCPToolCatalogSnapshot:
    desired = get_mcp_desired_state()
    bindings = {
        mcp_name: bind_transport_instance(mcp_name, config)
        for mcp_name, config in desired.all_mcps.items()
    }
    discovery = discover_catalog_outcomes(desired, bindings)
    routes, quarantined = _routes(bindings, discovery)
    routable_mcps = {route["mcp_name"] for route in routes.values()}
    availability = {
        mcp_name: _availability(discovery[mcp_name], mcp_name in routable_mcps)
        for mcp_name in desired.all_mcps
    }
    return MCPToolCatalogSnapshot.from_parts(desired, bindings, discovery, availability, routes, quarantined)


def _availability(outcome, routable: bool):
    online = False
    if outcome.status is MCPDiscoveryStatus.PROTOCOL_RESULT:
        online = outcome.protocol_result.status in {
            MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS,
            MCPToolsListProtocolStatus.SUCCESS_EMPTY,
        }
    return {"online": online, "routable": bool(routable), "status": outcome.status.name}


def _routes(
    bindings: dict[str, MCPTransportBindingOutcome],
    discovery: dict,
) -> tuple[dict, dict[str, tuple[str, ...]]]:
    candidates: dict[str, list[tuple[str, object, dict]]] = {}
    for mcp_name, outcome in discovery.items():
        if outcome.status is not MCPDiscoveryStatus.PROTOCOL_RESULT:
            continue
        result = outcome.protocol_result
        if result.status is not MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS:
            continue
        binding = bindings[mcp_name]
        if binding.status is not MCPTransportBindingStatus.BOUND:
            continue
        for tool in result.tools:
            name = str(tool.get("name", "")).strip()
            if name:
                candidates.setdefault(name, []).append((mcp_name, binding.transport, dict(tool)))
    routes = {}
    quarantined = {}
    for name, owners in candidates.items():
        if len(owners) == 1:
            mcp_name, transport, definition = owners[0]
            routes[name] = make_route(name, mcp_name, transport, definition)
        else:
            quarantined[name] = tuple(owner for owner, _transport, _definition in owners)
    return routes, quarantined
