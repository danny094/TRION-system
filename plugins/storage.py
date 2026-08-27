import shutil
from pathlib import Path
from typing import Any

from mcp.catalog_lifecycle import current_catalog_snapshot
from plugins.common import (
    load_plugin_manifest,
    load_plugin_meta,
    plugins_dir,
    plugin_dir,
    save_plugin_meta,
)


def list_plugins() -> list[dict[str, Any]]:
    root = plugins_dir()
    if not root.exists():
        return []
    items: list[dict[str, Any]] = []
    snapshot = current_catalog_snapshot()
    installed_mcps = set(snapshot.desired_mcps) if snapshot is not None else set()
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not (path / "plugin.json").exists():
            continue
        manifest = load_plugin_manifest(path.name)
        meta = load_plugin_meta(path.name)
        requires_mcp = manifest.get("requires_mcp") or []
        missing = [item for item in requires_mcp if item not in installed_mcps]
        items.append(
            {
                **manifest,
                "enabled": bool(meta.get("enabled", manifest.get("enabled", True))),
                "missing_mcp": missing,
            }
        )
    return items


def write_enabled(plugin_id: str, enabled: bool) -> None:
    meta = load_plugin_meta(plugin_id)
    meta["enabled"] = bool(enabled)
    save_plugin_meta(plugin_id, meta)


def remove_plugin(plugin_id: str) -> None:
    shutil.rmtree(plugin_dir(plugin_id), ignore_errors=True)


def plugin_exists(plugin_id: str) -> bool:
    return plugin_dir(plugin_id).exists()


def ensure_plugins_dir() -> Path:
    root = plugins_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root
