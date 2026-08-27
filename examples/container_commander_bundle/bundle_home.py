#!/usr/bin/env python3
import json

from bundle_common import AVAILABLE_HOME_CAPABILITIES, DEFAULT_WRITE_ROOTS, HOME_CAPABILITY_CLASSES, HOME_ROOT, MANIFEST_PATH, is_true


def is_home_container(labels):
    return is_true(labels.get("trion.home")) or str(labels.get("trion.role") or "").strip().lower() == "home"


def blueprint_id_from_labels(labels):
    return str(labels.get("trion.blueprint") or "").strip()


def parse_home_manifest(raw):
    try:
        parsed = json.loads(str(raw or "").strip())
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_home_manifest(container):
    try:
        result = container.exec_run(["cat", MANIFEST_PATH])
    except Exception:
        return {}
    exit_code = getattr(result, "exit_code", None)
    if exit_code is None or int(exit_code) != 0:
        return {}
    output = getattr(result, "output", b"")
    try:
        raw = output.decode("utf-8", errors="replace")
    except Exception:
        return {}
    return parse_home_manifest(raw)


def build_home_scope(labels, manifest):
    if not is_home_container(labels):
        return {}
    manifest = manifest if isinstance(manifest, dict) else {}
    roots = manifest.get("roots") if isinstance(manifest.get("roots"), dict) else {}
    rules = manifest.get("rules") if isinstance(manifest.get("rules"), dict) else {}
    allowed = [str(item) for item in list(rules.get("allowed_write_roots") or DEFAULT_WRITE_ROOTS) if str(item).strip()]
    available = list(AVAILABLE_HOME_CAPABILITIES)
    missing = [item for item in HOME_CAPABILITY_CLASSES if item not in available]
    verification_sources = ["container_inspect"] + (["home_manifest"] if manifest else [])
    return {
        "is_home": True,
        "home_id": str(manifest.get("home_id") or blueprint_id_from_labels(labels) or "trion-home"),
        "blueprint_id": str(manifest.get("blueprint_id") or blueprint_id_from_labels(labels) or "trion-home"),
        "owner_agent": str(manifest.get("owner_agent") or "trion"),
        "runtime_profile": str(labels.get("trion.profile") or manifest.get("runtime_profile") or "trion-home"),
        "home_root": str(roots.get("home") or HOME_ROOT),
        "manifest_path": MANIFEST_PATH,
        "manifest_readable": bool(manifest),
        "allowed_write_roots": allowed,
        "available_capability_classes": available,
        "missing_capability_classes": missing,
        "verification_sources": verification_sources,
    }
