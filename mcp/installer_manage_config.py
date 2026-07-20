"""
mcp.installer_manage_config
==============================
Normalisierung und atomare Registry-Anwendung fuer Custom-MCP-Config-Updates
(Toggle und PUT /config in mcp.installer_manage_routes).

Herausgeloest aus mcp/installer_manage_routes.py (P11.0 SP3, verhaltensneutraler
Split wegen Ueberschreitung der 200-Zeilen-Grenze aus Doc 07 durch die
Uninstall-Reihenfolge-Korrektur). Reine Verschiebung, keine Logikaenderung.
"""
from typing import Any, Dict

from mcp.config import get_mcp_config
from mcp.installer_common import (
    atomic_write_text,
    custom_config_path,
    custom_mcp_dir,
    save_custom_config,
)
from mcp.installer_manifest import build_tool_intent_mirror
from mcp.installer_registry import REGISTRY_LOCK, upsert_registry_entry


def validate_manifest_identity(
    name: str,
    normalized: Dict[str, Any],
    manifest_name: str,
) -> None:
    manifest_id = str(normalized.get("id", "")).strip()
    if manifest_id != name:
        field_name = "id" if manifest_name == "mcp.json" else "name"
        raise ValueError(f"Config field '{field_name}' must stay '{name}'")


def preserve_runtime_context(name: str, normalized: Dict[str, Any]) -> None:
    entry = normalized.get("entry") or {}
    if str(entry.get("type", "")).strip() != "stdio":
        return
    normalized["command"] = str(entry.get("command", "")).strip()
    normalized["cwd"] = str(custom_mcp_dir(name))


def preserve_tool_intents(name: str, normalized: Dict[str, Any]) -> None:
    """Fehlt die Bundle-Datei beim Toggle/Update (Bundle-Drift nach Install),
    wird der zuletzt in der Registry gespeicherte Mirror unveraendert
    uebernommen statt ihn implizit auf None zu setzen - sonst wuerde
    registry_entry_from_config()/upsert_registry_entry() (volles Ersetzen,
    kein Merge) einen zuvor vollstaendigen v2-Mirror loeschen, nur weil
    Toggle/Update gar nichts an den Tool-Capabilities aendern wollte
    (SP3-E, Codex-Pruefung ausstehend)."""
    path = custom_mcp_dir(name) / "tool_intents.json"
    if path.exists():
        normalized["tool_intents"] = build_tool_intent_mirror(
            path, bundle_version=str(normalized.get("version", "")).strip()
        )
    else:
        normalized["tool_intents"] = get_mcp_config(name).get("tool_intents")


def apply_config_and_registry_update(
    name: str,
    config: Dict[str, Any],
    normalized: Dict[str, Any],
) -> None:
    """Config+Registry+Rollback unter REGISTRY_LOCK als eine Transaktion
    (Codex Checkpoint 3, Runde 3 P1): schliesst die Race, bei der ein
    paralleler Rollback einen bereits erfolgreichen Registry-Write ueberschreibt.
    Der Registryschritt liest und schreibt ausschliesslich reine Customdaten;
    Core-Defaults bleiben ausserhalb dieser Transaktion."""
    if not isinstance(config, dict) or not isinstance(normalized, dict):
        raise TypeError("Config and normalized registry entry must be objects")
    path = custom_config_path(name)
    with REGISTRY_LOCK:
        previous_raw = path.read_text(encoding="utf-8") if path.exists() else None
        save_custom_config(name, config)
        try:
            upsert_registry_entry(name, normalized)
        except Exception:
            if previous_raw is not None:
                atomic_write_text(path, previous_raw)
            raise
