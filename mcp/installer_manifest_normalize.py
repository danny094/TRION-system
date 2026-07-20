"""
mcp.installer_manifest_normalize
==================================
Manifest-Format-spezifische Normalisierung (`mcp.json` / `config.json`).

Herausgeloest aus mcp/installer_manifest.py (P11.0 SP0, verhaltensneutraler
Split wegen Ueberschreitung der 200-Zeilen-Grenze aus Doc 07). Keine andere
Datei importiert diese Funktionen direkt; sie werden ausschliesslich von
`mcp.installer_manifest.normalize_manifest_payload()` aufgerufen.
"""
from typing import Any, Dict

from mcp.installer_common import InstallationError


def normalize_mcp_manifest(payload: Dict[str, Any]) -> Dict[str, Any]:
    required = {"schema_version", "id", "display_name", "version", "description", "transport", "entry"}
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise InstallationError(f"Missing required fields: {missing}")
    entry = payload.get("entry")
    if not isinstance(entry, dict):
        raise InstallationError("Field 'entry' must be an object")
    normalized = {
        "id": str(payload["id"]).strip(),
        "display_name": str(payload["display_name"]).strip(),
        "version": str(payload["version"]).strip(),
        "description": str(payload["description"]).strip(),
        "enabled": bool(payload.get("enabled", True)),
        "transport": str(payload["transport"]).strip() or "http",
        "schema_version": int(payload["schema_version"]),
        "entry": entry,
        "ui": payload.get("ui", {}),
        "plugin": payload.get("plugin"),
        "install": payload.get("install", {}),
        "manifest_format": "mcp.json",
    }
    _fill_runtime_fields(normalized, entry)
    return normalized


def normalize_legacy_manifest(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("tier") != "simple":
        raise InstallationError("Only Tier 1 (simple) MCPs supported")
    required = {"name", "url", "description"}
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise InstallationError(f"Missing required fields: {missing}")
    return {
        "id": str(payload["name"]).strip(),
        "display_name": str(payload.get("display_name") or payload["name"]).strip(),
        "version": str(payload.get("version", "0.1.0")).strip(),
        "description": str(payload["description"]).strip(),
        "enabled": bool(payload.get("enabled", True)),
        "transport": str(payload.get("transport", "http")).strip() or "http",
        "schema_version": 0,
        "entry": {"type": "remote_url", "url": str(payload["url"]).strip()},
        "ui": payload.get("ui", {}),
        "plugin": payload.get("plugin"),
        "install": payload.get("install", {}),
        "manifest_format": "config.json",
        "legacy_tier": "simple",
        "url": str(payload["url"]).strip(),
    }


def _fill_runtime_fields(normalized: Dict[str, Any], entry: Dict[str, Any]) -> None:
    entry_type = str(entry.get("type", "")).strip()
    if entry_type in {"remote_url", "http", "sse"}:
        normalized["url"] = str(entry.get("url", "")).strip()
    elif entry_type == "stdio":
        normalized["command"] = str(entry.get("command", "")).strip()
        if not normalized["command"]:
            raise InstallationError("Field 'entry.command' is required for stdio MCPs")
    else:
        raise InstallationError(f"Unsupported entry.type '{entry_type}'")
