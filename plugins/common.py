import json
from pathlib import Path
from typing import Any

from config.infra.paths import get_plugins_dir
from plugins.contracts import PLUGIN_META_FILE
from plugins.manifest import load_plugin_manifest as validate_plugin_manifest


def plugins_dir() -> Path:
    return Path(get_plugins_dir())


def plugin_dir(plugin_id: str) -> Path:
    return plugins_dir() / plugin_id


def plugin_manifest_path(plugin_id: str) -> Path:
    return plugin_dir(plugin_id) / "plugin.json"


def plugin_meta_path(plugin_id: str) -> Path:
    return plugin_dir(plugin_id) / PLUGIN_META_FILE


def load_plugin_manifest(plugin_id: str) -> dict[str, Any]:
    return validate_plugin_manifest(plugin_dir(plugin_id))


def load_plugin_meta(plugin_id: str) -> dict[str, Any]:
    path = plugin_meta_path(plugin_id)
    if not path.exists():
        return {"enabled": True}
    return json.loads(path.read_text(encoding="utf-8"))


def save_plugin_meta(plugin_id: str, meta: dict[str, Any]) -> None:
    plugin_meta_path(plugin_id).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def resolve_plugin_asset(plugin_id: str, relative_path: str) -> Path | None:
    if not relative_path.strip():
        return None
    root = plugin_dir(plugin_id).resolve()
    candidate = (root / relative_path).resolve()
    if not str(candidate).startswith(str(root)) or not candidate.exists() or not candidate.is_file():
        return None
    return candidate
