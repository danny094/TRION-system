"""
MCP Registry - Tool-Registrierung im Knowledge Graph.

Verantwortlich für:
- Auto-Registrierung aller Tools im sql-memory Knowledge Graph
- Detection Rules für den Classifier generieren
- System-Wissen abrufbar machen (welche Tools gibt es?)

Wird einmalig beim Hub-Start aufgerufen.
"""

from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from mcp.catalog_lifecycle import current_catalog_snapshot
from mcp.tool_result_contracts import MCPResultPresence, MCPToolCallStatus, MCPToolResultEnvelope
from utils.logger import log_debug, log_error, log_info, log_warning


SYSTEM_CONV_ID = "system"


class MCPRegistry:
    """Registriert Tools im Knowledge Graph und stellt Detection Rules bereit."""

    def __init__(self, hub: Any):
        self._hub = hub

    def register_all(self):
        """Registriert alle entdeckten Tools im Knowledge Graph (best effort)."""
        current_version = self._tool_registry_version()
        if not current_version:
            log_warning("[MCPRegistry] memory MCP nicht verfügbar — Tool-Registrierung übersprungen")
            return
        try:
            stored = self._hub.call_tool("memory_fact_load", {
                "conversation_id": SYSTEM_CONV_ID,
                "key": "tool_registry_version",
            })
            stored_version = self._result_value(stored) or ""
            if stored_version == current_version:
                log_info(f"[MCPRegistry] Tool-Registry aktuell (v{current_version})")
                return
        except Exception:
            pass

        try:
            self._save_fact("available_mcp_tools", self._tools_overview())
            snapshot = current_catalog_snapshot()
            routes = snapshot.routes_by_tool if snapshot else {}
            for name, route in routes.items():
                if not name.startswith("memory_"):
                    self._save_fact(f"tool_{name}", self._tool_info(name, route["tool_definition"]))
            self._save_fact("tool_registry_version", current_version)
            log_info(f"[MCPRegistry] Registrierung abgeschlossen: {len(routes)} tools (v{current_version})")
        except Exception as e:
            log_error(f"[MCPRegistry] Registrierung fehlgeschlagen: {e}")

    def detection_rules(self) -> str:
        """Legacy hook retained for compatibility; runtime exports no static rules."""
        return ""

    def get_system_knowledge(self, key: str) -> Optional[str]:
        """Ruft System-Wissen aus dem Knowledge Graph ab."""
        try:
            result = self._hub.call_tool("memory_fact_load", {
                "conversation_id": SYSTEM_CONV_ID,
                "key": key,
            })
            value = self._result_value(result)
            return str(value) if value is not None else None
        except Exception as e:
            log_error(f"[MCPRegistry] get_system_knowledge failed: {e}")
        return None

    # ── Private ────────────────────────────────────────────────────

    def _tool_registry_version(self) -> str:
        import hashlib
        snapshot = current_catalog_snapshot()
        names = sorted(snapshot.routes_by_tool) if snapshot else []
        return hashlib.md5(f"{len(names)}:{','.join(names)}".encode()).hexdigest()[:12]

    @staticmethod
    def _result_value(result: Any) -> Any:
        if not isinstance(result, MCPToolResultEnvelope):
            return None
        if result.status is not MCPToolCallStatus.SUCCESS:
            return None
        if result.structured_content_presence is not MCPResultPresence.VALUE:
            return None
        structured = result.structured_content
        value = structured.get("value")
        if value is None and isinstance(structured.get("result"), Mapping):
            value = structured["result"].get("value")
        return value

    def _tools_overview(self) -> str:
        by_mcp: Dict[str, List[str]] = {}
        snapshot = current_catalog_snapshot()
        for tool_name, route in (snapshot.routes_by_tool if snapshot else {}).items():
            by_mcp.setdefault(route["mcp_name"], []).append(tool_name)
        lines = ["Verfügbare MCP-Tools:"]
        for mcp_name, tools in by_mcp.items():
            lines.append(f"• {mcp_name}: {', '.join(tools)}")
        return " ".join(lines)

    def _tool_info(self, tool_name: str, tool_def: Dict) -> str:
        snapshot = current_catalog_snapshot()
        route = (snapshot.routes_by_tool if snapshot else {}).get(tool_name)
        mcp_name = route["mcp_name"] if route else "unknown"
        description = tool_def.get("description", "")
        schema = tool_def.get("inputSchema", {})
        props = schema.get("properties", {})
        required = schema.get("required", [])
        params = []
        for p_name, p_def in props.items():
            req = "required" if p_name in required else "optional"
            params.append(f"{p_name} ({p_def.get('type', 'any')}, {req})")
        base = f"Tool '{tool_name}' von '{mcp_name}': {description}. Parameter: {'; '.join(params) or 'keine'}"
        keywords = self._tool_intent_keywords(mcp_name, tool_name)
        if keywords:
            base += f". Keywords: {', '.join(keywords)}"
        return base

    def _tool_intent_keywords(self, mcp_name: str, tool_name: str) -> List[str]:
        snapshot = current_catalog_snapshot()
        config = (snapshot.desired_mcps.get(mcp_name) if snapshot else {}) or {}
        tool_intents = config.get("tool_intents")
        intents = (tool_intents or {}).get("tools") if isinstance(tool_intents, Mapping) else []
        if not isinstance(intents, (list, tuple)):
            return []
        for entry in intents:
            if not isinstance(entry, Mapping):
                continue
            if str(entry.get("name") or "").strip() != tool_name:
                continue
            raw = entry.get("keywords")
            if not isinstance(raw, (list, tuple)):
                return []
            return [str(item).strip() for item in raw if str(item).strip()]
        return []

    def _save_fact(self, key: str, value: str):
        try:
            result = self._hub.call_tool("memory_fact_save", {
                "conversation_id": SYSTEM_CONV_ID,
                "key": key,
                "value": value,
            })
            if isinstance(result, MCPToolResultEnvelope) and result.status is MCPToolCallStatus.SUCCESS:
                log_debug(f"[MCPRegistry] Saved: {key}")
            else:
                log_error(f"[MCPRegistry] Failed to save {key}: tool call failed")
        except Exception as e:
            log_error(f"[MCPRegistry] Failed to save {key}: {e}")
