"""
MCP Konfiguration - lädt die MCP-Server-Registry.

Liest aus mcp_registry.json im TRION-Root oder aus Umgebungsvariablen.
Ersetzt den alten mcp_registry.py Ansatz durch ein sauberes JSON-basiertes Config.
"""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Dict, Any

from mcp.desired_state import compose_mcp_desired_state, load_registry_source

_CONFIG_PATH = Path(os.getenv("MCP_REGISTRY_PATH", "/app/mcp_registry.json"))
_MEMORY_TOOL_INTENTS_PATH = Path(__file__).resolve().parent.parent / "memory" / "memory_mcp" / "tool_intents.json"


def _load_memory_tool_intents(bundle_version: str) -> Dict[str, Any]:
    """Bootstrapt die Memory-MCP-Mirror-Projektion ueber denselben
    Vertrag wie Install/Update/Toggle (`build_tool_intent_mirror()`,
    mcp.installer_tool_intents), statt die Bundle-Datei roh ueber
    `load_tool_intents()` einzulesen (SP3, Codex DECIDE: Core-/Memory-MCP
    durch denselben Projektionsvertrag bootstrapen). `bundle_version` kommt
    vom Aufrufer (`_default_mcps()`s `entry["version"]`) statt hier ein
    zweites Mal hartkodiert zu werden."""
    from mcp.installer_manifest import build_tool_intent_mirror
    from mcp.installer_common import InstallationError

    if not _MEMORY_TOOL_INTENTS_PATH.exists():
        return {}
    try:
        return build_tool_intent_mirror(_MEMORY_TOOL_INTENTS_PATH, bundle_version=bundle_version)
    except InstallationError:
        return {}


def _default_mcps() -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "enabled": True,
        "transport": "http",
        "url": os.getenv("MCP_BASE", "http://trion-memory:8081").rstrip("/") + "/mcp",
        "description": "Persistent memory, workspace, facts, graph and semantic search for TRION.",
        "display_name": "Memory MCP",
        "version": "1.0.0",
        "schema_version": 1,
        "ui": {
            "launchpad": {"enabled": False, "label": "Memory"},
            "settings": {"enabled": False, "mode": "config"},
        },
        "install": {
            "healthcheck": {"enabled": True},
            "runtime": {"kind": "service"},
        },
    }
    tool_intents = _load_memory_tool_intents(entry["version"])
    if tool_intents:
        entry["tool_intents"] = tool_intents
    return {"memory-mcp": entry}


def core_mcp_names() -> set[str]:
    """Namen der eingebauten MCPs (`_default_mcps()`). Diese tragen nie den
    `managed_by`-Marker (mcp.installer_registry.MANAGED_BY_INSTALLER) und
    sind daher fuer mcp.installer_reconcile.reconcile_tool_manifest_mirrors()
    komplett ausserhalb des Zustaendigkeitsbereichs (SP3, Codex DECIDE 2)."""
    return set(_default_mcps().keys())


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Project two already separated maps; collisions are never merged."""
    if set(base).intersection(override):
        raise ValueError("Core and custom MCP identifiers must be disjoint")
    return {**base, **override}


def _load_registry() -> Dict[str, Any]:
    defaults = _default_mcps()
    source = load_registry_source(_CONFIG_PATH, core_ids=set(defaults))
    desired = compose_mcp_desired_state(defaults, source)

    def mutable(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: mutable(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [mutable(item) for item in value]
        return value

    registry = _deep_merge(
        mutable(desired.core_mcps),
        mutable(desired.custom_mcps),
    )
    _restore_memory_tool_intents(registry)
    return registry


def _restore_memory_tool_intents(registry: Dict[str, Any]) -> None:
    """memory-mcp durchlaeuft nie Install/Update (kein Bundle, kein Receipt) -
    sein tool_intents-Mirror kommt ausschliesslich aus dem geshippten
    Bootstrap (`_default_mcps()`), nie aus einer hand-editierbaren
    mcp_registry.json. Die reine Custom-Registry darf den Core-Namen nicht
    enthalten; diese Wiederherstellung haelt zusaetzlich den bestehenden
    P11.0-SP3-Vertrag ('Mirror-Daten
    sind nicht manuell editierbar', vorher rot in
    tests/test_mcp_registry_memory_bootstrap.py)."""
    entry = registry.get("memory-mcp")
    if not isinstance(entry, dict):
        return
    bootstrap = _default_mcps()["memory-mcp"]
    if "tool_intents" in bootstrap:
        entry["tool_intents"] = bootstrap["tool_intents"]
    else:
        entry.pop("tool_intents", None)


def get_all_mcps() -> Dict[str, Any]:
    """Gibt alle konfigurierten MCP-Server zurück."""
    return _load_registry()


def get_registry_path() -> Path:
    """Gibt den Pfad zur MCP-Registry-Datei zurück."""
    return _CONFIG_PATH


def get_enabled_mcps() -> Dict[str, Any]:
    """Gibt nur aktivierte MCP-Server zurück."""
    return {
        name: config
        for name, config in _load_registry().items()
        if config.get("enabled", False)
    }


def get_mcp_config(mcp_name: str) -> Dict[str, Any]:
    """Gibt die Konfiguration eines einzelnen MCP-Servers zurück."""
    return _load_registry().get(mcp_name, {})
