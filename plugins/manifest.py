import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any

from mcp.installer_common import InstallationError
from plugins.contracts import ALLOWED_KINDS, ALLOWED_MOUNTS
from plugins.permissions import normalize_permissions

# W1/SP4.1: patchbare Modul-Konstante (Default `/tmp`), damit Tests die
# Extraktion in ein isoliertes `tmp_path`-Verzeichnis umleiten koennen, ohne
# das Produktionsverhalten (Default bleibt `/tmp`) zu aendern.
_TMP_DIR = Path("/tmp")


def extract_plugin_archive(filename: str | None, content: bytes) -> tuple[Path, dict[str, Any]]:
    temp_archive = _TMP_DIR / (filename or "plugin_upload.zip")
    temp_extract = _TMP_DIR / "plugin_extract"
    temp_archive.write_bytes(content)
    if temp_extract.exists():
        import shutil
        shutil.rmtree(temp_extract)
    suffix = (filename or "").lower()
    if suffix.endswith(".zip"):
        with zipfile.ZipFile(temp_archive, "r") as bundle:
            bundle.extractall(temp_extract)
    elif suffix.endswith((".tar", ".tar.gz", ".tgz")):
        with tarfile.open(temp_archive, "r:*") as bundle:
            bundle.extractall(temp_extract)
    else:
        raise InstallationError("Unsupported plugin archive format")
    root = resolve_plugin_root(temp_extract)
    return root, load_plugin_manifest(root)


def resolve_plugin_root(temp_extract: Path) -> Path:
    manifest = temp_extract / "plugin.json"
    if manifest.exists():
        return temp_extract
    candidates = [path for path in temp_extract.rglob("plugin.json") if not _skip_path(path.relative_to(temp_extract).parts)]
    if len(candidates) == 1:
        return candidates[0].parent
    if len(candidates) > 1:
        raise InstallationError("Multiple plugin.json files found in archive")
    raise InstallationError("plugin.json not found in plugin archive")


def load_plugin_manifest(root: Path) -> dict[str, Any]:
    payload = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise InstallationError("plugin.json must contain a JSON object")
    required = {"id", "name", "version", "kind", "mount", "entry"}
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise InstallationError(f"Missing required plugin fields: {missing}")
    kind = str(payload["kind"]).strip()
    mount = str(payload["mount"]).strip()
    if kind not in ALLOWED_KINDS:
        raise InstallationError(f"Unsupported plugin kind '{kind}'")
    if mount not in ALLOWED_MOUNTS or kind not in ALLOWED_MOUNTS[mount]:
        raise InstallationError(f"Unsupported plugin mount '{mount}' for kind '{kind}'")
    entry = str(payload["entry"]).strip()
    if not entry:
        raise InstallationError("Field 'entry' is required")
    if not (root / entry).exists():
        raise InstallationError(f"Plugin entry '{entry}' not found in bundle")
    plugin_id = str(payload["id"]).strip()
    if not plugin_id:
        raise InstallationError("Field 'id' must not be empty")
    return {
        "id": plugin_id,
        "name": str(payload["name"]).strip(),
        "version": str(payload["version"]).strip(),
        "author": str(payload.get("author", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "kind": kind,
        "mount": mount,
        "icon": str(payload.get("icon", "")).strip(),
        "entry": entry,
        "permissions": normalize_permissions(payload.get("permissions")),
        "requires_mcp": _string_list(payload.get("requires_mcp")),
        "requires": payload.get("requires", {}),
        "enabled": bool(payload.get("enabled", True)),
    }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InstallationError("requires_mcp must be a list")
    return [str(item).strip() for item in value if str(item).strip()]


def _skip_path(parts: tuple[str, ...]) -> bool:
    return any(part == "__MACOSX" or part.startswith(".") for part in parts)
