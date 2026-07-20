import shutil
from pathlib import Path
from typing import Any

from mcp.installer_common import InstallationError
from plugins.common import plugin_dir, save_plugin_meta
from plugins.manifest import extract_plugin_archive
from plugins.storage import ensure_plugins_dir, plugin_exists


def install_plugin_bundle(
    filename: str | None,
    content: bytes,
    installed_mcps: set[str],
) -> dict[str, Any]:
    extract_root, manifest = extract_plugin_archive(filename, content)
    plugin_id = str(manifest["id"])
    target_dir = plugin_dir(plugin_id)
    if plugin_exists(plugin_id):
        raise InstallationError(f"Plugin '{plugin_id}' already exists")
    missing_mcp = [item for item in manifest.get("requires_mcp", []) if item not in installed_mcps]
    if missing_mcp:
        raise InstallationError(f"Plugin '{plugin_id}' requires missing MCPs: {missing_mcp}")
    ensure_plugins_dir()
    shutil.move(str(extract_root), str(target_dir))
    save_plugin_meta(plugin_id, {"enabled": bool(manifest.get("enabled", True))})
    return manifest


def cleanup_failed_install(plugin_id: str | None, target_dir: Path | None) -> None:
    if plugin_id and plugin_dir(plugin_id).exists():
        shutil.rmtree(plugin_dir(plugin_id), ignore_errors=True)
        return
    if target_dir:
        shutil.rmtree(target_dir, ignore_errors=True)
