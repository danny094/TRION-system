"""
MCP Registry - Tool-Registrierung im Knowledge Graph.

Verantwortlich für:
- Auto-Registrierung aller Tools im sql-memory Knowledge Graph
- Detection Rules für den Classifier generieren
- System-Wissen abrufbar machen (welche Tools gibt es?)

Wird einmalig beim Hub-Start aufgerufen.
"""

from typing import Any, Dict, List, Optional

from utils.logger import log_debug, log_error, log_info, log_warning


SYSTEM_CONV_ID = "system"


class MCPRegistry:
    """Registriert Tools im Knowledge Graph und stellt Detection Rules bereit."""

    def __init__(self, hub: Any):
        self._hub = hub

    def register_all(self):
        """Registriert alle entdeckten Tools im Knowledge Graph (best effort)."""
        transport = self._memory_transport()
        if transport is None:
            log_warning("[MCPRegistry] memory MCP nicht verfügbar — Tool-Registrierung übersprungen")
            return
        current_version = self._tool_registry_version()

        try:
            stored = transport.call_tool("memory_fact_load", {
                "conversation_id": SYSTEM_CONV_ID,
                "key": "tool_registry_version",
            })
            stored_version = (stored or {}).get("value", "") if isinstance(stored, dict) else ""
            if stored_version == current_version:
                log_info(f"[MCPRegistry] Tool-Registry aktuell (v{current_version})")
                return
        except Exception:
            pass

        try:
            self._save_fact(transport, "available_mcp_tools", self._tools_overview())
            for name, definition in self._hub._tool_definitions.items():
                if not name.startswith("memory_"):
                    self._save_fact(transport, f"tool_{name}", self._tool_info(name, definition))
            self._save_fact(transport, "tool_registry_version", current_version)
            log_info(f"[MCPRegistry] Registrierung abgeschlossen: {len(self._hub._tool_definitions)} tools (v{current_version})")
        except Exception as e:
            log_error(f"[MCPRegistry] Registrierung fehlgeschlagen: {e}")

    def detection_rules(self) -> str:
        """Legacy hook retained for compatibility; runtime exports no static rules."""
        return ""

    def get_system_knowledge(self, key: str) -> Optional[str]:
        """Ruft System-Wissen aus dem Knowledge Graph ab."""
        transport = self._memory_transport()
        if transport is None:
            return None
        try:
            result = transport.call_tool("memory_fact_load", {
                "conversation_id": SYSTEM_CONV_ID,
                "key": key,
            })
            if isinstance(result, dict):
                return result.get("value") or result.get("content")
        except Exception as e:
            log_error(f"[MCPRegistry] get_system_knowledge failed: {e}")
        return None

    # ── Private ────────────────────────────────────────────────────

    def _tool_registry_version(self) -> str:
        import hashlib
        names = sorted(self._hub._tool_definitions.keys())
        return hashlib.md5(f"{len(names)}:{','.join(names)}".encode()).hexdigest()[:12]

    def _tools_overview(self) -> str:
        by_mcp: Dict[str, List[str]] = {}
        for tool_name, mcp_name in self._hub._tools_cache.items():
            by_mcp.setdefault(mcp_name, []).append(tool_name)
        lines = ["Verfügbare MCP-Tools:"]
        for mcp_name, tools in by_mcp.items():
            lines.append(f"• {mcp_name}: {', '.join(tools)}")
        return " ".join(lines)

    def _tool_info(self, tool_name: str, tool_def: Dict) -> str:
        mcp_name = self._hub._tools_cache.get(tool_name, "unknown")
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
        configs = getattr(self._hub, "_mcp_configs", {}) or {}
        config = configs.get(mcp_name) or {}
        intents = (config.get("tool_intents") or {}).get("tools") if isinstance(config.get("tool_intents"), dict) else []
        if not isinstance(intents, list):
            return []
        for entry in intents:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("name") or "").strip() != tool_name:
                continue
            raw = entry.get("keywords")
            if not isinstance(raw, list):
                return []
            return [str(item).strip() for item in raw if str(item).strip()]
        return []

    def _save_fact(self, transport: Any, key: str, value: str):
        try:
            transport.call_tool("memory_fact_save", {
                "conversation_id": SYSTEM_CONV_ID,
                "key": key,
                "value": value,
            })
            log_debug(f"[MCPRegistry] Saved: {key}")
        except Exception as e:
            log_error(f"[MCPRegistry] Failed to save {key}: {e}")

    def _memory_transport(self) -> Any | None:
        tool_owner = getattr(self._hub, "_tools_cache", {}).get("memory_fact_load")
        if tool_owner:
            transport = getattr(self._hub, "_transports", {}).get(tool_owner)
            if transport is not None:
                return transport
        for candidate in ("memory-mcp", "sql-memory", "trion-memory"):
            transport = getattr(self._hub, "_transports", {}).get(candidate)
            if transport is not None:
                return transport
        return None
