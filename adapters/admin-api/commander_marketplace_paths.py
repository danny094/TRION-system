"""
Shared marketplace path helpers.

This module is the local truth for repo/runtime marketplace path resolution.
"""

from __future__ import annotations

import os
from pathlib import Path


MARKETPLACE_DIR = os.environ.get("MARKETPLACE_DIR", "/app/data/marketplace")
MARKETPLACE_CATALOG_CACHE = os.environ.get(
    "MARKETPLACE_CATALOG_CACHE",
    os.path.join(MARKETPLACE_DIR, "catalog_cache.json"),
)
MARKETPLACE_DEFAULT_CATALOG_REPO = os.environ.get("TRION_BLUEPRINT_CATALOG_REPO", "")
MARKETPLACE_DEFAULT_CATALOG_BRANCH = os.environ.get("TRION_BLUEPRINT_CATALOG_BRANCH", "main")
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGE_DIR = REPO_ROOT / "marketplace" / "packages"
LOCAL_CONTAINER_ADDONS_DIR = REPO_ROOT / "intelligence_modules" / "container_addons"
RUNTIME_CONTAINER_ADDONS_DIR = Path(MARKETPLACE_DIR) / "container_addons"


def resolve_container_addon_install_root(install_root: str) -> tuple[str, Path]:
    raw_install_root = str(install_root or "intelligence_modules/container_addons").strip()
    normalized_install_root = raw_install_root.replace("\\", "/").strip().strip("/")
    if normalized_install_root == "intelligence_modules/container_addons":
        return raw_install_root, RUNTIME_CONTAINER_ADDONS_DIR

    target_root = (REPO_ROOT / normalized_install_root).resolve()
    try:
        target_root.relative_to(REPO_ROOT)
    except Exception as exc:
        raise ValueError(f"invalid_container_addon_install_root: {raw_install_root}") from exc
    return raw_install_root, target_root
