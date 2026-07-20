"""
Commander host-companion runtime helpers.

Local truth for package-manifest access and the remaining host-companion
runtime facade used by deploy setup/postchecks.
"""

from __future__ import annotations

from typing import Any, Dict

from commander_api.mcp_runtime import get_package_manifest_via_mcp, repair_host_companion_via_mcp


def get_package_manifest(blueprint_id: str) -> dict[str, Any]:
    return get_package_manifest_via_mcp(blueprint_id)


def ensure_host_companion(blueprint_id: str, overwrite: bool = False) -> dict[str, Any]:
    # v2 currently exposes a manifest/capability surface, not a real repair runtime.
    result = repair_host_companion_via_mcp(blueprint_id)
    if not isinstance(result, dict):
        return {
            "repaired": False,
            "skipped": True,
            "reason": "host_companion_runtime_invalid_result",
            "blueprint_id": blueprint_id,
            "overwrite": bool(overwrite),
        }
    normalized = dict(result)
    normalized.setdefault("overwrite", bool(overwrite))
    return normalized


def ensure_package_storage_scope(blueprint_id: str, *, blueprint: Any, manifest: Dict[str, Any] | None) -> dict[str, Any]:
    package_manifest = dict(manifest or {})
    runtime_views = package_manifest.get("runtime_storage_views")
    if not isinstance(runtime_views, dict):
        return {
            "ensured": False,
            "skipped": True,
            "reason": "package_storage_scope_not_configured",
            "blueprint_id": blueprint_id,
        }
    return {
        "ensured": False,
        "skipped": True,
        "reason": "package_storage_scope_runtime_not_implemented_in_v2",
        "blueprint_id": blueprint_id,
        "package_type": str(package_manifest.get("package_type", "")).strip(),
    }


def run_package_postchecks(
    blueprint_id: str,
    *,
    blueprint: Any,
    container: Any,
    manifest: Dict[str, Any] | None,
) -> dict[str, Any]:
    package_manifest = dict(manifest or {})
    postchecks = list(package_manifest.get("postchecks") or [])
    if not postchecks:
        return {"ok": True, "checks": [], "warnings": []}
    check_names = [
        str((item or {}).get("name") or f"postcheck_{index + 1}").strip() or f"postcheck_{index + 1}"
        for index, item in enumerate(postchecks)
    ]
    return {
        "ok": True,
        "checks": [{"name": name, "ok": True, "skipped": True} for name in check_names],
        "warnings": [
            {
                "name": "package_postchecks_runtime_not_implemented_in_v2",
                "detail": {
                    "message": "Package postchecks are declared but no runtime implementation exists in v2 yet.",
                    "blueprint_id": blueprint_id,
                    "checks": check_names,
                },
            }
        ],
    }
