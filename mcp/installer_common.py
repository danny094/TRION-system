import json
import os
import secrets
import stat
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException

from mcp.installer_health import is_online_flag, run_post_install_health_check
from mcp.installer_paths import (
    custom_config_path,
    custom_mcp_dir,
    custom_mcps_dir,
    is_installer_owned,
    receipt_path,
    resolve_icon_path,
    validate_mcp_id,
)

__all__ = [
    "MAX_SIZE",
    "InstallationError",
    "reload_hub_registry",
    "custom_config_path",
    "custom_mcp_dir",
    "custom_mcps_dir",
    "receipt_path",
    "is_installer_owned",
    "validate_mcp_id",
    "load_custom_config",
    "atomic_write_text",
    "save_custom_config",
    "resolve_icon_path",
    "is_online_flag",
    "run_post_install_health_check",
]

MAX_SIZE = 50 * 1024 * 1024


class InstallationError(Exception):
    """Aufraeumen bei Fehlschlag liegt beim Aufrufer (SP3 Lifecycle-
    Invariante in installer_install_routes._cleanup_failed_install():
    Mirror entfernen -> Hub reload -> Bundle entfernen), nicht hier - sonst
    zwei stille Implementierungen derselben Verantwortung (Doc 36 Regel 1)."""

    def __init__(self, message: str, target_dir: Path | None = None):
        self.message = message
        self.target_dir = target_dir


def reload_hub_registry(hub: Any) -> str:
    reload_fn = getattr(hub, "reload_registry", None)
    if callable(reload_fn):
        reload_fn()
        return "reload_registry"
    refresh_fn = getattr(hub, "refresh", None)
    if callable(refresh_fn):
        refresh_fn()
        return "refresh"
    raise InstallationError("Hub does not support registry reload/refresh")


def load_custom_config(name: str) -> Dict[str, Any]:
    path = custom_config_path(name)
    if not path.exists():
        raise HTTPException(
            404,
            f"Editable config for MCP '{name}' not found (core MCPs are read-only)",
        )
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise TypeError("Custom MCP config must be a JSON object")
        return loaded
    except Exception as exc:
        raise HTTPException(500, f"Failed to read config: {exc}") from exc


def atomic_write_text(path: Path, content: str) -> None:
    """Einziger atomarer Writer fuer Config UND Registry. Kollisionssicherer
    Tempname; der `except`-Block entfernt die Tempdatei bei jedem Fehler
    (Schreiben oder `os.replace()`), sonst bliebe physischer Muell zurueck.

    Rechte-Vertrag: existiert `path` bereits, geht dessen Modus direkt als
    Erzeugungsmodus an `_create_unique_tmp_file()` (Runde 6 P1; reproduziert:
    Ziel 0600, Tempdatei waehrend des Schreibens sonst 0644). Die Umask kann
    einen Erzeugungsmodus nur enger, nie weiter machen - die Tempdatei ist
    damit nie offener als das Ziel. `os.chmod()` (umask-unabhaengig) stellt
    danach den exakten Modus wieder her, falls die Umask Bits abschnitt.

    Fuer eine NEUE Zieldatei wird kein Standardmodus ueber `os.umask()`
    ermittelt - die Umask ist prozessweit, nicht threadlokal, ein
    kurzzeitiges Setzen oeffnete ein Race (Runde 5 P1; reproduziert: Umask
    0o077, paralleler Thread legt 0o666 statt 0o600 an). Stattdessen legt
    `_create_unique_tmp_file()` die Tempdatei per `O_CREAT | O_EXCL` mit
    `0o666` an; der Kernel maskiert das atomar mit der Prozess-Umask.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    fd, tmp_path = _create_unique_tmp_file(path, existing_mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        if existing_mode is not None:
            os.chmod(tmp_path, existing_mode)
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _create_unique_tmp_file(path: Path, existing_mode: int | None) -> tuple[int, Path]:
    """Legt eine kollisionssichere `.<datei>.<random>.tmp`-Datei neben `path`
    per `O_CREAT | O_EXCL` an. Erzeugungsmodus ist `existing_mode`, falls
    `path` existiert, sonst `0o666` - beides vom Kernel atomar mit der
    Prozess-Umask maskiert (kein os.umask()-Aufruf hier)."""
    create_mode = existing_mode if existing_mode is not None else 0o666
    for _ in range(100):
        candidate = path.parent / f".{path.name}.{secrets.token_hex(8)}.tmp"
        try:
            fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, create_mode)
        except FileExistsError:
            continue
        return fd, candidate
    raise InstallationError(f"Could not allocate a unique temp file next to {path}")


def save_custom_config(name: str, config: Dict[str, Any]) -> Path:
    if not isinstance(config, dict):
        raise TypeError("Custom MCP config must be a JSON object")
    path = custom_config_path(name)
    if not path.exists():
        raise HTTPException(
            404,
            f"Editable config for MCP '{name}' not found (core MCPs are read-only)",
        )
    atomic_write_text(path, json.dumps(config, indent=2, ensure_ascii=False))
    return path
