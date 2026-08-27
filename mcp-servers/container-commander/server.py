"""
Container Commander v2 — MCP Server Entry Point

The approved Phase-1 product surface contains exactly container_list,
container_inspect, container_logs, blueprint_list and blueprint_get.
This entry point still registers all 46 source-defined tools. That is tracked
P17-SP3 drift, not product, runtime-security or release approval. Doc24 remains
the sole product contract.
"""

from fastmcp import FastMCP

import tools_blueprints
import tools_dashboard
import tools_host_companion
import tools_marketplace
import tools_network
import tools_runtime
import tools_runtime_actions
import tools_volumes

mcp = FastMCP("container-commander")

# Registrierungsreihenfolge = exakte tools/list-Ordnung des Vor-Split-Servers.
tools_runtime.register(mcp)
tools_runtime_actions.register_cleanup(mcp)
tools_blueprints.register(mcp)
tools_network.register(mcp)
tools_dashboard.register(mcp)
tools_host_companion.register(mcp)
tools_marketplace.register(mcp)
tools_volumes.register(mcp)
tools_runtime_actions.register_lifecycle(mcp)

if __name__ == "__main__":
    mcp.run()
