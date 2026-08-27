import asyncio
import threading
from typing import Any, Dict, List, Optional

from mcp.catalog_builder import build_catalog_snapshot
from mcp.catalog_dispatch import dispatch_acquired_route
from mcp.catalog_contracts import MCPRegistryReloadConfirmation
from mcp.catalog_lifecycle import acquire_route, publish_catalog, revoke_catalog_routes
from mcp.hub_listing import list_mcps
from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope
from utils.logger import log_error, log_info, log_warning


class MCPHub:
    """Zentraler Router für alle MCP-Server."""

    def __init__(self):
        self._initialized = False
        self._lock = threading.RLock()

    def initialize(self):
        """Verbindet alle konfigurierten MCP-Server und entdeckt ihre Tools.

        Reconciliation laeuft genau hier, einmalig vor dem ersten Lesen der
        enabled MCP-Configs (P11.0 SP3, Codex DECIDE 1: idempotente Startup-
        Reparatur, kein Hot-Path - `reload_registry()` ruft sie bewusst
        NICHT erneut auf)."""
        with self._lock:
            if self._initialized:
                return
            log_info("[MCPHub] Initializing...")
            self._reconcile_tool_manifest_mirrors()
            publish_catalog(build_catalog_snapshot())
            self._initialized = True
            log_info("[MCPHub] Ready")
            self._register_tools_in_memory()

    @staticmethod
    def _reconcile_tool_manifest_mirrors() -> None:
        from mcp.installer_reconcile import reconcile_tool_manifest_mirrors

        result = reconcile_tool_manifest_mirrors()
        if result["repaired"] or result["removed"] or result["unresolved"]:
            log_info(f"[MCPHub] Reconcile at startup: {result}")

    def list_tools(self) -> List[Dict[str, Any]]:
        from collections.abc import Mapping

        self.initialize()
        from mcp.catalog_lifecycle import current_catalog_snapshot

        def plain(value: Any) -> Any:
            if isinstance(value, Mapping):
                return {key: plain(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [plain(item) for item in value]
            return value

        snapshot = current_catalog_snapshot()
        if snapshot is None:
            return []
        return [plain(route["tool_definition"]) for route in snapshot.routes_by_tool.values()]

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolResultEnvelope:
        self.initialize()
        try:
            token = acquire_route(tool_name)
        except KeyError:
            log_error(f"[MCPHub] Tool not found: {tool_name}")
            return MCPToolResultEnvelope(
                MCPToolCallStatus.PROTOCOL_FAILURE,
                protocol_error={
                    "code": -32601,
                    "message": f"Tool '{tool_name}' not found",
                },
            )
        except Exception as e:
            return MCPToolResultEnvelope(
                MCPToolCallStatus.TRANSPORT_FAILURE,
                transport_diagnostic=str(e) or "MCP hub routing failure",
            )
        log_info(f"[MCPHub] Calling {tool_name} via {token.mcp_name}")
        try:
            return dispatch_acquired_route(token, arguments)
        except Exception as e:
            log_error(f"[MCPHub] Tool call failed: {e}")
            return MCPToolResultEnvelope(
                MCPToolCallStatus.TRANSPORT_FAILURE,
                transport_diagnostic=str(e) or "MCP hub tool-call failure",
            )

    async def call_tool_async(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolResultEnvelope:
        return await asyncio.to_thread(self.call_tool, tool_name, arguments)

    def get_mcp_for_tool(self, tool_name: str) -> Optional[str]:
        self.initialize()
        from mcp.catalog_lifecycle import current_catalog_snapshot

        snapshot = current_catalog_snapshot()
        route = snapshot.routes_by_tool.get(tool_name) if snapshot else None
        return route["mcp_name"] if route else None

    def list_mcps(self) -> List[Dict[str, Any]]:
        self.initialize()
        return list_mcps(self)

    def refresh(self):
        return self.reload_registry()

    def reload_registry(self):
        with self._lock:
            log_info("[MCPHub] Reloading registry...")
            candidate = build_catalog_snapshot()
            revocation = revoke_catalog_routes(self._shutdown_transport, replacement_snapshot=candidate)
            confirmation = MCPRegistryReloadConfirmation(candidate, revocation)
            self._initialized = True

        log_info("[MCPHub] Reload complete")
        self._register_tools_in_memory()
        return confirmation

    def shutdown(self):
        revoke_catalog_routes(self._shutdown_transport)
        log_info("[MCPHub] Shutdown complete")

    def _register_tools_in_memory(self):
        try:
            from mcp.registry import MCPRegistry
            MCPRegistry(self).register_all()
        except Exception as e:
            log_warning(f"[MCPHub] Tool registry sync skipped: {e}")

    def _shutdown_transport(self, transport: Any):
        shutdown = getattr(transport, "shutdown", None)
        if callable(shutdown):
            shutdown()


# ── Singleton ──────────────────────────────────────────────────────

_hub: Optional[MCPHub] = None


def get_hub() -> MCPHub:
    global _hub
    if _hub is None:
        _hub = MCPHub()
    return _hub
