import asyncio
import threading
from typing import Any, Dict, List, Optional

from mcp.hub_discovery import (
    discover_tools,
    reload_on_tool_miss,
    refresh_incomplete_discovery,
)
from mcp.hub_listing import list_mcps
from mcp.transports import HTTPTransport, SSETransport, STDIOTransport
from utils.logger import log_debug, log_error, log_info, log_warning


class MCPHub:
    """Zentraler Router für alle MCP-Server."""

    def __init__(self):
        self._transports: Dict[str, Any] = {}
        self._tools_cache: Dict[str, str] = {}
        self._tool_definitions: Dict[str, Dict] = {}
        self._mcp_configs: Dict[str, Dict[str, Any]] = {}
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
            from mcp.config import get_enabled_mcps
            for mcp_name, config in get_enabled_mcps().items():
                try:
                    self._init_transport(mcp_name, config)
                    discover_tools(self, mcp_name)
                except Exception as e:
                    log_error(f"[MCPHub] Failed to init {mcp_name}: {e}")
            self._initialized = True
            log_info(f"[MCPHub] Ready — {len(self._tools_cache)} tools from {len(self._transports)} servers")
            self._register_tools_in_memory()

    @staticmethod
    def _reconcile_tool_manifest_mirrors() -> None:
        from mcp.installer_reconcile import reconcile_tool_manifest_mirrors

        result = reconcile_tool_manifest_mirrors()
        if result["repaired"] or result["removed"] or result["unresolved"]:
            log_info(f"[MCPHub] Reconcile at startup: {result}")

    def _init_transport(self, mcp_name: str, config: Dict):
        transport_type = config.get("transport", "http")
        if transport_type in {"http", "https"}:
            self._transports[mcp_name] = HTTPTransport(config.get("url", ""), config.get("api_key", ""))
        elif transport_type == "sse":
            self._transports[mcp_name] = SSETransport(config.get("url", ""), config.get("api_key", ""))
        elif transport_type == "stdio":
            self._transports[mcp_name] = STDIOTransport(config.get("command", ""), cwd=config.get("cwd", ""))
        self._mcp_configs[mcp_name] = dict(config)
        log_debug(f"[MCPHub] {mcp_name}: {transport_type} transport")

    def list_tools(self) -> List[Dict[str, Any]]:
        self.initialize()
        refresh_incomplete_discovery(self)
        with self._lock:
            return list(self._tool_definitions.values())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        self.initialize()
        with self._lock:
            mcp_name = self._tools_cache.get(tool_name)
            transport = self._transports.get(mcp_name) if mcp_name else None

        if not mcp_name:
            reload_on_tool_miss(self, tool_name)
            with self._lock:
                mcp_name = self._tools_cache.get(tool_name)
                transport = self._transports.get(mcp_name) if mcp_name else None
        if not mcp_name:
            log_error(f"[MCPHub] Tool not found: {tool_name}")
            return {"error": f"Tool '{tool_name}' not found"}
        if not transport:
            log_error(f"[MCPHub] No transport for: {mcp_name}")
            return {"error": f"MCP '{mcp_name}' not available"}

        log_info(f"[MCPHub] Calling {tool_name} via {mcp_name}")
        try:
            return transport.call_tool(tool_name, arguments)
        except Exception as e:
            log_error(f"[MCPHub] Tool call failed: {e}")
            return {"error": str(e)}

    async def call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        return await asyncio.to_thread(self.call_tool, tool_name, arguments)

    def get_mcp_for_tool(self, tool_name: str) -> Optional[str]:
        self.initialize()
        with self._lock:
            mcp_name = self._tools_cache.get(tool_name)
        if mcp_name:
            return mcp_name
        reload_on_tool_miss(self, tool_name)
        with self._lock:
            return self._tools_cache.get(tool_name)

    def list_mcps(self) -> List[Dict[str, Any]]:
        self.initialize()
        return list_mcps(self)

    def refresh(self):
        self.reload_registry()

    def reload_registry(self):
        with self._lock:
            log_info("[MCPHub] Reloading registry...")
            from mcp.config import get_enabled_mcps

            enabled_mcps = get_enabled_mcps()
            previous = set(self._transports.keys())
            current = set(enabled_mcps.keys())

            removed = previous - current
            for mcp_name in removed:
                self._shutdown_transport(mcp_name)
                self._transports.pop(mcp_name, None)
                self._mcp_configs.pop(mcp_name, None)

            self._tools_cache.clear()
            self._tool_definitions.clear()

            for mcp_name, config in enabled_mcps.items():
                if self._transport_needs_reload(mcp_name, config):
                    self._shutdown_transport(mcp_name)
                    self._transports.pop(mcp_name, None)
                if mcp_name not in self._transports:
                    try:
                        self._init_transport(mcp_name, config)
                    except Exception as e:
                        log_error(f"[MCPHub] Failed to init {mcp_name}: {e}")
                        continue
                else:
                    self._mcp_configs[mcp_name] = dict(config)
                discover_tools(self, mcp_name)

            self._initialized = True

        log_info(f"[MCPHub] Reload complete: {len(self._tools_cache)} tools from {len(self._transports)} servers")
        self._register_tools_in_memory()

    def shutdown(self):
        for mcp_name, transport in self._transports.items():
            if isinstance(transport, STDIOTransport):
                transport.shutdown()
        log_info("[MCPHub] Shutdown complete")

    def _register_tools_in_memory(self):
        try:
            from mcp.registry import MCPRegistry
            MCPRegistry(self).register_all()
        except Exception as e:
            log_warning(f"[MCPHub] Tool registry sync skipped: {e}")

    def _shutdown_transport(self, mcp_name: str):
        transport = self._transports.get(mcp_name)
        if isinstance(transport, STDIOTransport):
            transport.shutdown()

    def _transport_needs_reload(self, mcp_name: str, config: Dict[str, Any]) -> bool:
        return self._mcp_configs.get(mcp_name) != dict(config)


# ── Singleton ──────────────────────────────────────────────────────

_hub: Optional[MCPHub] = None


def get_hub() -> MCPHub:
    global _hub
    if _hub is None:
        _hub = MCPHub()
    return _hub
