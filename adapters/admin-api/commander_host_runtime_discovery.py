"""
Commander host-runtime discovery helpers.

Local truth for the remaining host-runtime requirement facade used by deploy
postchecks.
"""

from __future__ import annotations

from typing import Any, Dict


def run_package_host_runtime_checks(blueprint_id: str, *, manifest: Dict[str, Any] | None) -> dict[str, Any]:
    package_manifest = dict(manifest or {})
    requirements = package_manifest.get("host_runtime_requirements")
    if not isinstance(requirements, dict):
        return {"ok": True, "checks": [], "infos": [], "warnings": []}

    names = [
        str(name or "").strip()
        for name in requirements.keys()
        if str(name or "").strip()
    ]
    if not names:
        return {"ok": True, "checks": [], "infos": [], "warnings": []}

    return {
        "ok": True,
        "checks": [{"name": name, "ok": True, "skipped": True} for name in names],
        "infos": [],
        "warnings": [
            {
                "name": "host_runtime_requirements_not_implemented_in_v2",
                "detail": {
                    "message": "Host runtime requirements are declared but no verification runtime exists in v2 yet.",
                    "blueprint_id": blueprint_id,
                    "requirements": names,
                },
            }
        ],
    }
