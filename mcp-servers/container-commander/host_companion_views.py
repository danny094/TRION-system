from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_PACKAGE_DIR = REPO_ROOT / "marketplace" / "packages"


def _load_local_package_manifest(blueprint_id: str) -> dict[str, Any] | None:
    manifest_path = LOCAL_PACKAGE_DIR / str(blueprint_id or "").strip() / "package.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def get_package_manifest(blueprint_id: str) -> dict[str, Any]:
    manifest = _load_local_package_manifest(blueprint_id)
    return {"blueprint_id": blueprint_id, "manifest": manifest or {}}


def _host_companion_config(blueprint_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _load_local_package_manifest(blueprint_id) or {}
    host_companion = manifest.get("host_companion")
    host_companion = host_companion if isinstance(host_companion, dict) else {}
    return manifest, host_companion


def check_host_companion(blueprint_id: str) -> dict[str, Any]:
    manifest, host_companion = _host_companion_config(blueprint_id)
    configured = bool(host_companion)
    return {
        "checked": True,
        "blueprint_id": blueprint_id,
        "configured": configured,
        "status": "configured" if configured else "not_configured",
        "host_companion": dict(host_companion),
        "package_manifest_present": bool(manifest),
        "package_type": str(manifest.get("package_type", "")).strip(),
    }


def repair_host_companion(blueprint_id: str) -> dict[str, Any]:
    manifest, host_companion = _host_companion_config(blueprint_id)
    if not host_companion:
        return {
            "repaired": False,
            "skipped": True,
            "reason": "host_companion_not_configured",
            "blueprint_id": blueprint_id,
        }
    return {
        "repaired": False,
        "skipped": True,
        "reason": "host_companion_runtime_not_implemented_in_v2",
        "blueprint_id": blueprint_id,
        "host_companion": dict(host_companion),
        "package_manifest_present": bool(manifest),
    }


def uninstall_host_companion(blueprint_id: str) -> dict[str, Any]:
    manifest, host_companion = _host_companion_config(blueprint_id)
    if not host_companion:
        return {
            "uninstalled": False,
            "skipped": True,
            "reason": "host_companion_not_configured",
            "removed_paths": [],
            "blueprint_id": blueprint_id,
        }
    return {
        "uninstalled": False,
        "skipped": True,
        "reason": "host_companion_runtime_not_implemented_in_v2",
        "removed_paths": [],
        "blueprint_id": blueprint_id,
        "host_companion": dict(host_companion),
        "package_manifest_present": bool(manifest),
    }
