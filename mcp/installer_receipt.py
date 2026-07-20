import json
from pathlib import Path
from typing import Any, Dict, List


RECEIPT_FILE = ".trion-install.json"


def build_install_receipt(
    mcp_id: str,
    manifest: Dict[str, Any],
    target_dir: Path,
    registry_path: Path,
    runtime_kind: str = "",
    runtime_created_paths: list[str] | None = None,
) -> Dict[str, Any]:
    """Receipt-Vertrag (P11.0-Plan SP3): mcp-ID, Pfade, Version und Mirror-
    Hash - keine zweite, stale Kopie der vollen `tool_intents` (Codex
    Checkpoint 4 P1). Der Hash kommt aus dem bereits gebauten Mirror
    (`manifest['tool_intents']['source_sha256']`), nicht aus einer eigenen
    Neuberechnung - sonst zwei Quellen fuer denselben Wert."""
    mirror = manifest.get("tool_intents") or {}
    return {
        "mcp_id": mcp_id,
        "version": manifest.get("version", ""),
        "manifest_format": manifest.get("manifest_format", "unknown"),
        "owned_paths": [str(target_dir)],
        "registry_paths": [str(registry_path)],
        "runtime_kind": runtime_kind,
        "runtime_created_paths": list(runtime_created_paths or []),
        "ui": manifest.get("ui", {}),
        "plugin": manifest.get("plugin"),
        "tool_intents_hash": mirror.get("source_sha256", "") if isinstance(mirror, dict) else "",
    }


def receipt_path_for_dir(target_dir: Path) -> Path:
    return target_dir / RECEIPT_FILE


def write_install_receipt(target_dir: Path, receipt: Dict[str, Any]) -> Path:
    path = receipt_path_for_dir(target_dir)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_install_receipt(target_dir: Path) -> Dict[str, Any]:
    path = receipt_path_for_dir(target_dir)
    return json.loads(path.read_text(encoding="utf-8"))


def owned_paths_from_receipt(name: str, target_dir: Path) -> List[Path]:
    """Liefert nur Pfade, die nachweislich zum erwarteten Bundle gehoeren.

    Das Receipt liegt im Bundle-Verzeichnis und ist damit bundle-/
    angreifer-kontrollierter Inhalt, kein vertrauenswuerdiger Code-Wert
    (Codex Checkpoint 4 P0: ein manipuliertes `owned_paths` konnte sonst
    einen beliebigen Pfad - z.B. ausserhalb von `custom_mcps/` - an
    `shutil.rmtree()` durchreichen). Zwei Pruefungen vor jeder Nutzung:
    1. `mcp_id` im Receipt muss exakt dem angefragten `name` entsprechen.
    2. jeder einzelne Pfad muss nach Aufloesung gleich `target_dir` sein
       oder darunter liegen - alles andere wird verworfen, nie geloescht.
    `target_dir` selbst stammt beim Aufrufer immer aus `name` (code-
    konstruiert), nie aus dieser Datei.
    """
    receipt = load_install_receipt(target_dir)
    if str(receipt.get("mcp_id", "")) != name:
        raise ValueError(
            f"Receipt mcp_id {receipt.get('mcp_id')!r} does not match expected MCP '{name}'"
        )
    resolved_target = target_dir.resolve()
    validated: List[Path] = []
    for raw in receipt.get("owned_paths", []):
        candidate = Path(str(raw)).resolve()
        if candidate == resolved_target or resolved_target in candidate.parents:
            validated.append(candidate)
    return validated
