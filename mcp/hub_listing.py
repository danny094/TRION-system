"""
mcp.hub_listing
==================
Projektion der Registry+Live-Hub-Zustand fuer die Admin-UI (`MCPHub.list_mcps()`).

Verhaltensneutraler Split aus `mcp/hub.py` (P11.0 SP3, Doc 07 200-Zeilen-
Grenze durch den Reconcile-Aufruf in `MCPHub.initialize()` ueberschritten).
Reine Verschiebung, keine Logikaenderung. Eigenes Modul statt Ablage in
`mcp.hub_discovery` (Live-Discovery/Health), da dies eine andere
Verantwortung ist: Registry-Konfiguration + Live-Status fuer die UI
zusammenfuehren, nicht Tools beim Server entdecken (Doc 07 Single-
Responsibility-pro-Datei).
"""
from typing import Any, Dict, List


def list_mcps(hub: Any) -> List[Dict[str, Any]]:
    from mcp.config import get_all_mcps

    with hub._lock:
        transports = dict(hub._transports)
        tools_cache = dict(hub._tools_cache)
    result = []
    for mcp_name, config in get_all_mcps().items():
        transport = transports.get(mcp_name)
        tools_count = sum(1 for _, m in tools_cache.items() if m == mcp_name)
        result.append({
            "name": mcp_name,
            "display_name": config.get("display_name", "") or mcp_name,
            "version": config.get("version", ""),
            "enabled": config.get("enabled", False),
            "transport": config.get("transport", "http"),
            "url": config.get("url", "") or config.get("command", ""),
            "description": config.get("description", ""),
            "ui": config.get("ui", {}),
            "has_settings": bool(((config.get("ui") or {}).get("settings") or {}).get("enabled")),
            "launchpad_enabled": bool(((config.get("ui") or {}).get("launchpad") or {}).get("enabled")),
            "launchpad_label": ((config.get("ui") or {}).get("launchpad") or {}).get("label", ""),
            "settings_mode": ((config.get("ui") or {}).get("settings") or {}).get("mode", ""),
            "online": transport.health_check() if transport else False,
            "tools_count": tools_count,
        })
    return result
