from __future__ import annotations

import io
import json
import os
import tarfile
from datetime import datetime, timezone
from typing import Any
from urllib.request import urlopen

from blueprint_store import get_blueprint
from blueprint_write import create_blueprint, import_blueprint_yaml, update_blueprint
from marketplace_views import (
    MARKETPLACE_DIR,
    STARTER_BLUEPRINTS,
    _ensure_marketplace_dir,
    _http_get_text,
    _load_catalog_cache,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _yaml_dump(data: dict[str, Any]) -> str:
    try:
        import yaml  # type: ignore

        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except ModuleNotFoundError:
        lines: list[str] = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                rendered = json.dumps(value, ensure_ascii=False)
            elif value is None:
                rendered = "null"
            elif isinstance(value, bool):
                rendered = "true" if value else "false"
            else:
                rendered = str(value)
            lines.append(f"{key}: {rendered}")
        return "\n".join(lines) + ("\n" if lines else "")


def _yaml_load(yaml_content: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(yaml_content) or {}
    except ModuleNotFoundError:
        data = {}
        for raw_line in yaml_content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip()
            value = raw_value.strip()
            if value in {"", "null", "~"}:
                parsed: Any = None
            elif value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
                parsed = value[1:-1]
            elif value in {"true", "false"}:
                parsed = value == "true"
            elif value.startswith("[") or value.startswith("{"):
                parsed = json.loads(value)
            else:
                parsed = value
            data[key] = parsed
    if not isinstance(data, dict):
        raise ValueError("yaml must describe an object")
    return data


def _add_string_to_tar(tar: tarfile.TarFile, name: str, content: str) -> None:
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def install_starter(starter_id: str) -> dict[str, Any]:
    starter = next((item for item in STARTER_BLUEPRINTS if item["id"] == starter_id), None)
    if not starter:
        return {"error": f"Starter '{starter_id}' not found"}
    existing = get_blueprint(starter_id).get("blueprint")
    if isinstance(existing, dict) and existing:
        return {"exists": True, "blueprint": existing}
    payload = dict(starter)
    payload.pop("allowed_domains", None)
    result = create_blueprint(payload)
    blueprint = result.get("blueprint") if isinstance(result, dict) else {}
    return {"installed": True, "blueprint": blueprint}


def export_bundle(blueprint_id: str) -> str | None:
    detail = get_blueprint(blueprint_id).get("blueprint")
    if not isinstance(detail, dict) or not detail:
        return None
    definition = dict(detail.get("definition") or {})
    _ensure_marketplace_dir()
    filename = f"{blueprint_id}.trion-bundle.tar.gz"
    filepath = os.path.join(MARKETPLACE_DIR, filename)
    meta = {
        "id": detail.get("blueprint_id", blueprint_id),
        "name": detail.get("name", ""),
        "version": detail.get("version", ""),
        "exported_at": _now(),
        "tags": definition.get("tags", []),
    }
    with tarfile.open(filepath, "w:gz") as tar:
        _add_string_to_tar(tar, "blueprint.yaml", _yaml_dump(definition))
        _add_string_to_tar(tar, "meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
        dockerfile = str(definition.get("dockerfile") or "")
        if dockerfile:
            _add_string_to_tar(tar, "Dockerfile", dockerfile)
        readme = f"# {detail.get('name', blueprint_id)}\n\n{detail.get('description', '')}\n"
        _add_string_to_tar(tar, "README.md", readme)
    return filename


def import_bundle(bundle_bytes: bytes, *, filename: str = "", overwrite: bool = False) -> dict[str, Any] | None:
    try:
        with tarfile.open(fileobj=io.BytesIO(bundle_bytes), mode="r:gz") as tar:
            blueprint_file = tar.extractfile("blueprint.yaml")
            if blueprint_file is None:
                return {"error": "bundle_missing_blueprint_yaml"}
            yaml_content = blueprint_file.read().decode("utf-8")
            data = _yaml_load(yaml_content)
            blueprint_id = str(data.get("id") or "").strip()
            existing = get_blueprint(blueprint_id).get("blueprint") if blueprint_id else None
            if overwrite and isinstance(existing, dict) and blueprint_id:
                imported = update_blueprint(blueprint_id, data)
            else:
                imported = import_blueprint_yaml(yaml_content)
            result = dict(imported) if isinstance(imported, dict) else {"error": "import_failed"}
            result["imported"] = True
            if filename:
                result["filename"] = filename
            return result
    except Exception as exc:
        return {"error": str(exc)}


def install_catalog_blueprint(blueprint_id: str, overwrite: bool = False) -> dict[str, Any]:
    rows = _load_catalog_cache().get("blueprints")
    catalog = rows if isinstance(rows, list) else []
    target = next((row for row in catalog if str(row.get("id", "")).strip() == str(blueprint_id).strip()), None)
    if not isinstance(target, dict):
        return {"error": f"catalog_blueprint_not_found: {blueprint_id}"}
    bundle_url = str(target.get("bundle_url", "")).strip()
    if bundle_url:
        with urlopen(bundle_url, timeout=30) as resp:
            raw_bundle = resp.read()
        result = import_bundle(raw_bundle, filename=f"{blueprint_id}.trion-bundle.tar.gz", overwrite=overwrite)
        if isinstance(result, dict):
            result["source"] = target
        return result if isinstance(result, dict) else {"error": "catalog_import_failed"}
    yaml_url = str(target.get("yaml_url", "")).strip()
    if not yaml_url:
        return {"error": f"catalog_blueprint_missing_yaml_url: {blueprint_id}"}
    raw_yaml = _http_get_text(yaml_url, timeout=20)
    data = _yaml_load(raw_yaml)
    blueprint_id_value = str(data.get("id") or target.get("id") or "").strip()
    existing = get_blueprint(blueprint_id_value).get("blueprint") if blueprint_id_value else None
    if overwrite and isinstance(existing, dict) and blueprint_id_value:
        imported = update_blueprint(blueprint_id_value, data)
    else:
        imported = import_blueprint_yaml(raw_yaml)
    result = dict(imported) if isinstance(imported, dict) else {"error": "catalog_import_failed"}
    result["source"] = target
    if isinstance(result, dict) and "exists" not in result and "error" not in result:
        result["installed"] = True
    return result
