"""
Shared marketplace bundle helpers.

This module is the local truth for bundle export/import and catalog installs.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import tarfile
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from commander_blueprint_write import create_blueprint, update_blueprint
from commander_deploy_blueprints import get_blueprint, resolve_blueprint
from commander_marketplace_catalog import get_catalog_cache, http_get_bytes, http_get_text
from commander_marketplace_paths import (
    LOCAL_CONTAINER_ADDONS_DIR,
    LOCAL_PACKAGE_DIR,
    MARKETPLACE_DIR,
    resolve_container_addon_install_root,
)
from models import Blueprint, NetworkMode, ResourceLimits


logger = logging.getLogger(__name__)
_SECRET_REF_RE = re.compile(r"^\{\{\s*SECRET\s*:\s*([A-Za-z0-9_]+)\s*\}\}$")


def _add_string_to_tar(tar: tarfile.TarFile, name: str, content: str) -> None:
    data = content.encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def _load_local_package_manifest(blueprint_id: str) -> Optional[Dict]:
    manifest_path = LOCAL_PACKAGE_DIR / blueprint_id / "package.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("[Marketplace] Failed to read local package manifest for %s", blueprint_id)
        return None


def _add_package_dir_to_tar(tar: tarfile.TarFile, blueprint_id: str) -> None:
    package_dir = LOCAL_PACKAGE_DIR / blueprint_id
    if not package_dir.exists():
        return
    for file_path in sorted(package_dir.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(package_dir)
        if str(rel) == "package.json":
            continue
        data = file_path.read_bytes()
        info = tarfile.TarInfo(name=f"package/{rel.as_posix()}")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def _container_addon_source_paths(package_manifest: Dict) -> List[Path]:
    addon_cfg = package_manifest.get("container_addons") if isinstance(package_manifest, dict) else {}
    addon_cfg = addon_cfg if isinstance(addon_cfg, dict) else {}
    entries: List[str] = []
    for key in ("profiles", "dependencies", "files", "root_files"):
        values = addon_cfg.get(key)
        if isinstance(values, list):
            entries.extend(str(item).strip() for item in values if str(item).strip())

    paths: List[Path] = []
    seen: set[str] = set()
    for rel in entries:
        normalized = rel.replace("\\", "/").strip().lstrip("/")
        if not normalized or ".." in normalized.split("/"):
            continue
        if normalized in seen:
            continue
        source = LOCAL_CONTAINER_ADDONS_DIR / normalized
        if source.exists() and source.is_file():
            paths.append(source)
            seen.add(normalized)
    return paths


def _add_container_addons_to_tar(tar: tarfile.TarFile, package_manifest: Dict) -> None:
    for source in _container_addon_source_paths(package_manifest):
        rel = source.relative_to(LOCAL_CONTAINER_ADDONS_DIR)
        data = source.read_bytes()
        info = tarfile.TarInfo(name=f"container_addons/{rel.as_posix()}")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def _sanitize_package_member(name: str) -> Optional[str]:
    normalized = str(name or "").strip().replace("\\", "/")
    if not normalized.startswith("package/"):
        return None
    rel = normalized[len("package/") :].strip("/")
    if not rel or ".." in rel.split("/"):
        return None
    return rel


def _sanitize_container_addon_member(name: str) -> Optional[str]:
    normalized = str(name or "").strip().replace("\\", "/")
    if not normalized.startswith("container_addons/"):
        return None
    rel = normalized[len("container_addons/") :].strip("/")
    if not rel or ".." in rel.split("/"):
        return None
    return rel


def _ensure_marketplace_dir() -> None:
    os.makedirs(MARKETPLACE_DIR, exist_ok=True)


def _convert_env_secrets(env: Dict) -> Dict[str, str]:
    out: Dict[str, str] = {}
    source = env if isinstance(env, dict) else {}
    for k, v in source.items():
        key = str(k).strip()
        if not key:
            continue
        value = str(v)
        match = _SECRET_REF_RE.match(value.strip())
        if match:
            out[key] = f"vault://{match.group(1).upper()}"
        else:
            out[key] = value
    return out


def _install_bundle_package(blueprint_id: str, tar: tarfile.TarFile, package_manifest: Dict) -> Dict:
    _ensure_marketplace_dir()
    package_root = Path(MARKETPLACE_DIR) / "packages" / blueprint_id
    package_root.mkdir(parents=True, exist_ok=True)
    written: List[str] = []

    (package_root / "package.json").write_text(
        json.dumps(package_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    written.append("package.json")

    for member in tar.getmembers():
        rel = _sanitize_package_member(member.name)
        if not rel or not member.isfile():
            continue
        extracted = tar.extractfile(member)
        if extracted is None:
            continue
        target = package_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(extracted.read())
        written.append(rel)

    return {
        "installed": True,
        "package_id": blueprint_id,
        "package_type": str(package_manifest.get("package_type", "composite_addon")).strip() or "composite_addon",
        "root": str(package_root),
        "files": written,
    }


def _install_bundle_container_addons(blueprint_id: str, tar: tarfile.TarFile, package_manifest: Dict) -> Dict:
    addon_cfg = package_manifest.get("container_addons") if isinstance(package_manifest, dict) else {}
    addon_cfg = addon_cfg if isinstance(addon_cfg, dict) else {}
    install_root, target_root = resolve_container_addon_install_root(
        addon_cfg.get("install_root", "intelligence_modules/container_addons")
    )

    written: List[str] = []
    for member in tar.getmembers():
        rel = _sanitize_container_addon_member(member.name)
        if not rel or not member.isfile():
            continue
        extracted = tar.extractfile(member)
        if extracted is None:
            continue
        target = target_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(extracted.read())
        written.append(rel)

    return {
        "installed": bool(written),
        "package_id": blueprint_id,
        "install_root": install_root,
        "root": str(target_root),
        "files": written,
    }


def export_bundle(blueprint_id: str) -> Optional[str]:
    bp = resolve_blueprint(blueprint_id)
    if not bp:
        return None

    _ensure_marketplace_dir()

    bp_dict = bp.model_dump(mode="json")
    bp_yaml = yaml.dump(bp_dict, default_flow_style=False, allow_unicode=True)
    meta = {
        "id": bp.id,
        "name": bp.name,
        "version": "1.0.0",
        "author": "TRION",
        "exported_at": datetime.utcnow().isoformat(),
        "tags": bp.tags,
        "checksum": hashlib.sha256(bp_yaml.encode()).hexdigest(),
    }
    package_manifest = _load_local_package_manifest(bp.id)
    if package_manifest:
        meta["package_type"] = str(package_manifest.get("package_type", "composite_addon")).strip() or "composite_addon"

    filename = f"{blueprint_id}.trion-bundle.tar.gz"
    filepath = os.path.join(MARKETPLACE_DIR, filename)

    with tarfile.open(filepath, "w:gz") as tar:
        _add_string_to_tar(tar, "blueprint.yaml", bp_yaml)
        _add_string_to_tar(tar, "meta.json", json.dumps(meta, indent=2))
        if bp.dockerfile:
            _add_string_to_tar(tar, "Dockerfile", bp.dockerfile)
        readme = f"# {bp.name}\n\n{bp.description}\n\n## Tags\n{', '.join(bp.tags)}\n"
        _add_string_to_tar(tar, "README.md", readme)
        if package_manifest:
            _add_string_to_tar(tar, "package.json", json.dumps(package_manifest, indent=2, ensure_ascii=False))
            _add_package_dir_to_tar(tar, bp.id)
            _add_container_addons_to_tar(tar, package_manifest)

    logger.info("[Marketplace] Exported: %s", filename)
    return filename


def list_bundles() -> List[Dict]:
    if not os.path.exists(MARKETPLACE_DIR):
        return []

    result = []
    for filename in sorted(os.listdir(MARKETPLACE_DIR)):
        if not filename.endswith(".trion-bundle.tar.gz"):
            continue
        filepath = os.path.join(MARKETPLACE_DIR, filename)
        stat = os.stat(filepath)

        meta = {}
        try:
            with tarfile.open(filepath, "r:gz") as tar:
                meta_raw = tar.extractfile("meta.json").read().decode("utf-8")
                meta = json.loads(meta_raw)
        except Exception:
            pass

        result.append(
            {
                "filename": filename,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "id": meta.get("id", filename.replace(".trion-bundle.tar.gz", "")),
                "name": meta.get("name", ""),
                "version": meta.get("version", ""),
                "tags": meta.get("tags", []),
                "exported_at": meta.get("exported_at", ""),
            }
        )

    return result


def import_bundle(filepath_or_bytes, filename: str = "", overwrite: bool = False) -> Optional[Dict]:
    try:
        tar_args = (filepath_or_bytes, "r:gz") if isinstance(filepath_or_bytes, str) else None
        with (
            tarfile.open(*tar_args) if tar_args else tarfile.open(fileobj=io.BytesIO(filepath_or_bytes), mode="r:gz")
        ) as tar:
            bp_yaml = tar.extractfile("blueprint.yaml").read().decode("utf-8")
            bp_data = yaml.safe_load(bp_yaml)

            try:
                meta_raw = tar.extractfile("meta.json").read().decode("utf-8")
                meta = json.loads(meta_raw)
            except Exception:
                meta = {}
            try:
                package_raw = tar.extractfile("package.json").read().decode("utf-8")
                package_manifest = json.loads(package_raw)
            except Exception:
                package_manifest = None

            if meta.get("checksum"):
                actual = hashlib.sha256(bp_yaml.encode()).hexdigest()
                if actual != meta["checksum"]:
                    logger.warning("[Marketplace] Checksum mismatch for %s", filename)

            resources = ResourceLimits(**(bp_data.pop("resources", {})))
            network = NetworkMode(bp_data.pop("network", "internal"))

            for key in list(bp_data.keys()):
                if key not in Blueprint.model_fields:
                    bp_data.pop(key)

            bp = Blueprint(resources=resources, network=network, **bp_data)

            existing = get_blueprint(bp.id)
            if existing:
                if not overwrite:
                    return {"error": f"Blueprint '{bp.id}' already exists", "blueprint": existing.model_dump()}
                update_blueprint(bp.id, bp.model_dump())
                created = get_blueprint(bp.id)
            else:
                create_blueprint(bp.model_dump())
                created = get_blueprint(bp.id)

            package_info = None
            addon_info = None
            if isinstance(package_manifest, dict):
                package_info = _install_bundle_package(bp.id, tar, package_manifest)
                addon_info = _install_bundle_container_addons(bp.id, tar, package_manifest)

        logger.info("[Marketplace] Imported: %s", bp.id)
        result = {"imported": True, "blueprint": created.model_dump() if created else bp.model_dump(), "meta": meta}
        if package_info:
            result["package"] = package_info
        if addon_info:
            result["container_addons"] = addon_info
        return result
    except Exception as exc:
        logger.error("[Marketplace] Import failed: %s", exc)
        return {"error": str(exc)}


def install_catalog_blueprint(blueprint_id: str, overwrite: bool = False) -> Dict:
    catalog = get_catalog_cache()
    rows = catalog.get("blueprints") if isinstance(catalog.get("blueprints"), list) else []
    target = next((r for r in rows if str(r.get("id", "")).strip() == str(blueprint_id).strip()), None)
    if not target:
        return {"error": f"catalog_blueprint_not_found: {blueprint_id}"}

    bundle_url = str(target.get("bundle_url", "")).strip()
    if bundle_url:
        raw_bundle = http_get_bytes(bundle_url, timeout=30)
        result = import_bundle(raw_bundle, filename=f"{blueprint_id}.trion-bundle.tar.gz", overwrite=overwrite)
        if isinstance(result, dict):
            result["source"] = target
        return result

    yaml_url = str(target.get("yaml_url", "")).strip()
    if not yaml_url:
        return {"error": f"catalog_blueprint_missing_yaml_url: {blueprint_id}"}

    raw_yaml = http_get_text(yaml_url, timeout=20)
    data = yaml.safe_load(raw_yaml)
    if not isinstance(data, dict):
        return {"error": f"invalid_blueprint_yaml: {blueprint_id}"}

    payload = dict(data)
    payload["id"] = str(payload.get("id") or target["id"]).strip()
    payload["name"] = str(payload.get("name") or target["name"]).strip()
    payload["description"] = str(payload.get("description") or target.get("description", "")).strip()
    payload["icon"] = str(payload.get("icon") or target.get("icon", "📦")).strip() or "📦"
    payload["tags"] = payload.get("tags") if isinstance(payload.get("tags"), list) else target.get("tags", [])
    payload["network"] = str(payload.get("network") or target.get("network", "internal")).strip().lower() or "internal"
    payload["environment"] = _convert_env_secrets(payload.get("environment") or {})

    profile = target.get("health_profile") if isinstance(target.get("health_profile"), dict) else {}
    health_cfg = payload.get("healthcheck") if isinstance(payload.get("healthcheck"), dict) else {}
    if profile:
        if "interval_seconds" not in health_cfg and "interval_seconds" in profile:
            health_cfg["interval_seconds"] = profile["interval_seconds"]
        if "timeout_seconds" not in health_cfg and "timeout_seconds" in profile:
            health_cfg["timeout_seconds"] = profile["timeout_seconds"]
        if "retries" not in health_cfg and "retries" in profile:
            health_cfg["retries"] = profile["retries"]
        if "ready_timeout_seconds" not in health_cfg and "ready_timeout_seconds" in profile:
            health_cfg["ready_timeout_seconds"] = profile["ready_timeout_seconds"]
    payload["healthcheck"] = health_cfg

    safe_payload = {k: v for k, v in payload.items() if k in Blueprint.model_fields}
    bp = Blueprint(**safe_payload)

    existing = get_blueprint(bp.id)
    if existing and not overwrite:
        return {"exists": True, "blueprint": existing.model_dump(), "source": target}
    if existing and overwrite:
        update_blueprint(bp.id, bp.model_dump())
        updated = get_blueprint(bp.id)
        return {"updated": True, "blueprint": updated.model_dump() if updated else bp.model_dump(), "source": target}

    create_blueprint(bp.model_dump())
    created = get_blueprint(bp.id)
    return {"installed": True, "blueprint": created.model_dump() if created else bp.model_dump(), "source": target}
