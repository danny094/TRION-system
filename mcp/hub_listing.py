"""
mcp.hub_listing
==================
Projektion der Registry+Live-Hub-Zustand fuer die Admin-UI (`MCPHub.list_mcps()`).

Verhaltensneutraler Split aus `mcp/hub.py` (P11.0 SP3, Doc 07 200-Zeilen-
Grenze durch den Reconcile-Aufruf in `MCPHub.initialize()` ueberschritten).
Seit P14-SP2/3-C liest diese Projektion nur den publizierten Catalog-Snapshot:
Registry-Konfiguration + Catalog-Availability fuer die UI zusammenfuehren,
nicht Tools beim Server entdecken (Doc 07 Single-Responsibility-pro-Datei).
"""
from typing import Any, Dict, List


def list_mcps(hub: Any) -> List[Dict[str, Any]]:
    from collections.abc import Mapping

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
    result = []
    for mcp_name, config in snapshot.desired_mcps.items():
        availability = snapshot.availability_by_mcp[mcp_name]
        tools_count = sum(1 for route in snapshot.routes_by_tool.values() if route["mcp_name"] == mcp_name)
        ui = plain(config.get("ui", {}))
        result.append({
            "name": mcp_name,
            "display_name": config.get("display_name", "") or mcp_name,
            "version": config.get("version", ""),
            "enabled": config.get("enabled", False),
            "transport": config.get("transport", "http"),
            "url": config.get("url", "") or config.get("command", ""),
            "description": config.get("description", ""),
            "ui": ui,
            "has_settings": bool(((ui or {}).get("settings") or {}).get("enabled")),
            "launchpad_enabled": bool(((ui or {}).get("launchpad") or {}).get("enabled")),
            "launchpad_label": ((ui or {}).get("launchpad") or {}).get("label", ""),
            "settings_mode": ((ui or {}).get("settings") or {}).get("mode", ""),
            "online": bool(availability.get("online", False)),
            "tools_count": tools_count,
        })
    return result
