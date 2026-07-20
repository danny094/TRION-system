"""
mcp.installer_manifest
========================
Archiv-Extraktion und Manifest-Dispatch fuer MCP-Bundle-Uploads.

P11.0 SP0: verhaltensneutral aus der vorherigen 212-Zeilen-Datei aufgeteilt
(Doc 07: max. 200 Zeilen pro Datei). Manifest-Format-Normalisierung liegt in
`mcp.installer_manifest_normalize`, Tool-Intent-Laden in
`mcp.installer_tool_intents`. `extract_archive`, `load_tool_intents` und
`normalize_manifest_payload` bleiben unter diesem Modulpfad importierbar,
damit kein bestehender Call-Site-Import (mcp/config.py,
mcp/installer_install_routes.py, mcp/installer_manage_routes.py,
adapters/tool_runner_bridge.py, tests/test_mcp_installer_manifest.py)
geaendert werden muss.

P11.0 SP2: `_attach_tool_intents()` baut den Mirror jetzt ueber
`build_tool_intent_mirror()` (SP1) statt ueber `load_tool_intents()`, damit
Install denselben Mirror-Builder verwendet wie Update/Toggle in
`mcp.installer_manage_routes`.

W1/SP4.1: `_TMP_DIR` ist eine patchbare Modul-Konstante (Default `/tmp`),
damit Tests die Extraktion in ein isoliertes `tmp_path`-Verzeichnis umleiten
koennen, ohne das Produktionsverhalten (Default bleibt `/tmp`) zu aendern.
"""
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple

from mcp.installer_common import InstallationError
from mcp.installer_manifest_normalize import normalize_legacy_manifest, normalize_mcp_manifest
from mcp.installer_tool_intents import build_tool_intent_mirror, load_tool_intents

__all__ = [
    "extract_archive",
    "resolve_extract_root",
    "load_bundle_manifest",
    "normalize_manifest_payload",
    "load_tool_intents",
    "build_tool_intent_mirror",
]

_TMP_DIR = Path("/tmp")


def extract_archive(filename: str | None, content: bytes, tmp_dir: Path | None = None) -> Tuple[Path, Dict[str, Any]]:
    base_dir = tmp_dir or _TMP_DIR
    temp_archive = base_dir / (filename or "mcp_upload.zip")
    temp_extract = base_dir / "mcp_extract"
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
        raise InstallationError("Unsupported archive format")
    extract_root = resolve_extract_root(temp_extract)
    config = load_bundle_manifest(extract_root)
    return extract_root, config


def resolve_extract_root(temp_extract: Path) -> Path:
    if any((temp_extract / name).exists() for name in ("mcp.json", "config.json")):
        return temp_extract
    manifests = _candidate_manifest_paths(temp_extract)
    if len(manifests) == 1:
        return manifests[0].parent
    if len(manifests) > 1:
        raise InstallationError("Multiple mcp.json/config.json files found in archive")
    raise InstallationError("mcp.json/config.json not found in bundle archive")


def load_bundle_manifest(extract_root: Path) -> Dict[str, Any]:
    mcp_manifest = extract_root / "mcp.json"
    if mcp_manifest.exists():
        normalized = normalize_manifest_payload(mcp_manifest.name, _load_json(mcp_manifest))
        _attach_tool_intents(normalized, extract_root)
        return normalized
    legacy_manifest = extract_root / "config.json"
    if legacy_manifest.exists():
        normalized = normalize_manifest_payload(legacy_manifest.name, _load_json(legacy_manifest))
        _attach_tool_intents(normalized, extract_root)
        return normalized
    raise InstallationError("mcp.json/config.json not found")


def normalize_manifest_payload(filename: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if filename == "mcp.json":
        return normalize_mcp_manifest(payload)
    if filename == "config.json":
        return normalize_legacy_manifest(payload)
    raise InstallationError(f"Unsupported manifest file '{filename}'")


def _candidate_manifest_paths(temp_extract: Path) -> list[Path]:
    manifests: list[Path] = []
    for path in temp_extract.rglob("*"):
        if path.name not in {"mcp.json", "config.json"}:
            continue
        relative_parts = path.relative_to(temp_extract).parts
        if _skip_archive_path(relative_parts):
            continue
        manifests.append(path)
    return manifests


def _skip_archive_path(parts: tuple[str, ...]) -> bool:
    return any(part == "__MACOSX" or part.startswith(".") for part in parts)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise InstallationError(f"Invalid JSON in {path.name}") from exc
    if not isinstance(raw, dict):
        raise InstallationError(f"{path.name} must contain a JSON object")
    return raw


def _attach_tool_intents(normalized: Dict[str, Any], extract_root: Path) -> None:
    tool_intents_path = extract_root / "tool_intents.json"
    if tool_intents_path.exists():
        normalized["tool_intents"] = build_tool_intent_mirror(
            tool_intents_path, bundle_version=str(normalized.get("version", "")).strip()
        )
