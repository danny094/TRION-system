"""
mcp.hub_discovery
====================
Live-Discovery- und Health-Hilfsfunktionen fuer `MCPHub` (P11.0 SP3,
verhaltensneutraler Split wegen Ueberschreitung der 200-Zeilen-Grenze aus
Doc 07 durch den Reconcile-Aufruf in `MCPHub.initialize()`).

Reine Verschiebung, keine Logikaenderung: dieselbe Signatur-Konvention wie
`mcp.installer_common.reload_hub_registry(hub)` - freie Funktionen, die den
Hub als erstes Argument von aussen entgegennehmen, statt gebundene Methoden
zu sein. `hub._lock`, `hub._transports`, `hub._tools_cache` und
`hub._tool_definitions` bleiben Hub-interner Zustand; diese Funktionen lesen
und schreiben ihn ueber den Hub selbst, importieren ihn aber nicht eigenstaendig.
"""
from typing import Any

from utils.logger import log_error, log_info


def discover_tools(hub: Any, mcp_name: str) -> None:
    transport = hub._transports.get(mcp_name)
    if not transport:
        return
    try:
        tools = transport.list_tools()
        for tool in tools:
            name = tool.get("name", "")
            if name:
                hub._tools_cache[name] = mcp_name
                hub._tool_definitions[name] = tool
        log_info(f"[MCPHub] {mcp_name}: {len(tools)} tools discovered")
    except Exception as e:
        log_error(f"[MCPHub] {mcp_name}: tool discovery failed: {e}")


def reload_on_tool_miss(hub: Any, tool_name: str) -> None:
    with hub._lock:
        if tool_name in hub._tools_cache:
            return
    log_info(f"[MCPHub] Tool miss for {tool_name}; reloading registry once")
    hub.reload_registry()


def refresh_incomplete_discovery(hub: Any) -> None:
    with hub._lock:
        incomplete = [
            mcp_name
            for mcp_name, transport in hub._transports.items()
            if tools_count_for_mcp(hub, mcp_name) == 0 and transport_healthy(transport)
        ]
    if not incomplete:
        return
    log_info(f"[MCPHub] Incomplete discovery for {', '.join(incomplete)}; reloading registry")
    hub.reload_registry()


def tools_count_for_mcp(hub: Any, mcp_name: str) -> int:
    return sum(1 for _, owner in hub._tools_cache.items() if owner == mcp_name)


def transport_healthy(transport: Any) -> bool:
    health_check = getattr(transport, "health_check", None)
    if not callable(health_check):
        return False
    try:
        return bool(health_check())
    except Exception:
        return False
