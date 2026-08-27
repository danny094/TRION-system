"""
mcp.installer_registry
=========================
Atomarer Mirror-Writer fuer `mcp_registry.json` (P11.0 SP2).

`installer_install_routes.py` und `installer_manage_routes.py` rufen fuer
Install, Update und Toggle ausschliesslich `upsert_registry_entry()` auf und
bauen ihren `tool_intents`-Wert vorher einheitlich ueber
`mcp.installer_tool_intents.build_tool_intent_mirror()` (SP1), bevor er Teil
von `config` wird.

SP2-Vertrag (von Codex bestaetigt, kein Downgrade-/Semver-Check):
- Mirror-`bundle_version` muss der Manifest-`version` entsprechen.
- jedes per-Tool `tool_intent_meta` muss exakt dem Mirror-Header entsprechen.
- `source_sha256` muss zur tatsaechlichen Toolprojektion passen: die von
  `installer_tool_intents.project_tool()` denormalisierten Felder
  (`tool_intent_meta`, `capability_complete`, `missing_capability_fields`)
  werden entfernt, der Rest erneut gehasht und mit `source_sha256`
  verglichen. Codex-Befund (Checkpoint 3, Runde 1): ohne diese Pruefung
  akzeptierte eine nachtraeglich am Mirror manipulierte Toolbeschreibung den
  alten Hash.
- die denormalisierten Felder selbst werden gegen eine frische Projektion
  ueber dieselbe `project_tool()`-Funktion geprueft (volle Gleichheit, keine
  duplizierte Pflichtfeldlogik hier). Codex-Befund (Checkpoint 3, Runde 2):
  die Runde-1-Pruefung entfernte `capability_complete`/
  `missing_capability_fields` vor dem Hash, verglich sie aber nie gegen den
  tatsaechlichen Toolinhalt - ein unvollstaendiges v2-Tool konnte nachtraeglich
  auf `capability_complete=True` gesetzt werden, ohne den Hash zu beruehren.
- alle drei Pruefungen laufen vor dem Schreiben; bei Verstoss wird gar nicht
  geschrieben (`InstallationError`), der alte Registry-Stand bleibt gueltig.
- der gesamte Mirror wird als Einheit ersetzt, nie teilweise gemergt - das
  ergibt sich bereits daraus, dass `registry_entry_from_config()` pro Aufruf
  einen frischen Eintrag baut.
- gleiche Version mit gleichem oder geaendertem Hash ist erlaubt (kein
  Downgrade-Schutz in P11.0; das waere eine eigene Policy).
- Schreiben nutzt denselben atomaren Writer wie die Custom-Config
  (`installer_common.atomic_write_text()`: eindeutiger Tempname,
  except-Cleanup bei Fehlern, Erhalt bestehender Dateirechte vor
  `os.replace()`) statt einer eigenen, dazu redundanten Implementierung.
- `REGISTRY_LOCK` ist oeffentlich und reentrant (`threading.RLock`):
  `installer_manage_routes._apply_config_and_registry_update()` haelt es ueber
  Config-Schreiben + Registry-Update + Rollback als eine Transaktion, dieses
  Modul haelt es zusaetzlich intern fuer den Registry-Read-Modify-Write -
  ohne Reentrancy waere das ein Deadlock. Codex-Befund (Checkpoint 3, Runde
  3 P1): ohne eine gemeinsame Sperre ueber die gesamte Transaktion konnte ein
  paralleler Rollback einen bereits erfolgreichen Registry-Write einer
  anderen Anfrage durch Wiederherstellen der alten Config widersprechen.
"""
import fcntl
import json
import os
import threading
from contextlib import contextmanager
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, Iterator

from mcp.config import core_mcp_names, get_registry_path
from mcp.desired_state import MCPRegistrySourceStatus, load_registry_source
from mcp.installer_common import atomic_write_text
from mcp.installer_registry_validation import (
    _assert_mirror_consistency,
    _assert_mirror_hash_matches_projection,
)

REGISTRY_LOCK = threading.RLock()

MANAGED_BY_INSTALLER = "trion_installer"


def registry_entry_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """`managed_by` (SP3) wird ausschliesslich hier gesetzt, nie aus dem
    Bundle uebernommen - es ist der Eigentumsbeweis, den der Reconciler
    (mcp/installer_reconcile.py) braucht, um installer-verwaltete Eintraege
    von Core-/Memory-Eintraegen (mcp.config._default_mcps()) zu unterscheiden,
    auch wenn deren Bundle-Verzeichnis spaeter verschwindet."""
    entry = {
        "enabled": bool(config.get("enabled", True)),
        "transport": str(config.get("transport", "http") or "http"),
        "url": str(config.get("url", "") or ""),
        "description": str(config.get("description", "") or ""),
        "display_name": str(config.get("display_name", "") or ""),
        "version": str(config.get("version", "") or ""),
        "schema_version": int(config.get("schema_version", 0) or 0),
        "entry": config.get("entry", {}),
        "ui": config.get("ui", {}),
        "plugin": config.get("plugin"),
        "install": config.get("install", {}),
        "tool_intents": config.get("tool_intents"),
        "managed_by": MANAGED_BY_INSTALLER,
    }
    command = str(config.get("command", "") or "")
    if command:
        entry["command"] = command
    cwd = str(config.get("cwd", "") or "")
    if cwd:
        entry["cwd"] = cwd
    return entry


def upsert_registry_entry(name: str, config: Dict[str, Any]) -> None:
    entry = registry_entry_from_config(config)
    _assert_mirror_consistency(config)
    if name in core_mcp_names():
        raise ValueError("Core MCP entries cannot be persisted as custom data")
    with registry_write_transaction():
        registry = _custom_registry_for_write()
        registry[name] = entry
        _write_registry(registry)


def remove_registry_entry(name: str) -> None:
    if name in core_mcp_names():
        raise ValueError("Core MCP entries cannot be removed by the custom writer")
    with registry_write_transaction():
        registry = _custom_registry_for_write()
        if name in registry:
            del registry[name]
            _write_registry(registry)


@contextmanager
def registry_write_transaction(path: Path | None = None) -> Iterator[Path]:
    """Serialize registry read-modify-write across threads and processes."""
    target = path or get_registry_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_LOCK:
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            fcntl.flock(directory_fd, fcntl.LOCK_EX)
            yield target
        finally:
            fcntl.flock(directory_fd, fcntl.LOCK_UN)
            os.close(directory_fd)


def _custom_registry_for_write() -> Dict[str, Any]:
    outcome = load_registry_source(get_registry_path(), core_ids=core_mcp_names())
    if outcome.status is MCPRegistrySourceStatus.MISSING:
        return {}
    if outcome.status is not MCPRegistrySourceStatus.VALID:
        raise ValueError(f"Registry source status blocks mutation: {outcome.status.name}")
    return _mutable_registry(outcome.custom_registry or {})


def _mutable_registry(value: Any) -> Any:
    def mutable(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: mutable(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [mutable(item) for item in value]
        return value

    return mutable(value)


def _write_registry(registry: Dict[str, Any]) -> None:
    payload = _registry_json_bytes(registry)
    path = get_registry_path()
    atomic_write_text(path, payload.decode("utf-8"))


def _registry_json_bytes(registry: Dict[str, Any]) -> bytes:
    if set(registry).intersection(core_mcp_names()):
        raise ValueError("Registry writer accepts pure custom data only")
    if not all(
        isinstance(name, str) and bool(name.strip()) and isinstance(config, dict)
        for name, config in registry.items()
    ):
        raise ValueError("Registry writer requires an object of MCP objects")
    return (json.dumps(registry, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def migrate_legacy_core_entries(*, apply: bool = False) -> Dict[str, Any]:
    """Compatibility facade for the explicit operator migration."""
    from mcp.installer_registry_migration import migrate_legacy_core_entries as migrate

    return migrate(
        path=get_registry_path(),
        core_ids=core_mcp_names(),
        apply=apply,
    )
