"""Explicit, fail-closed migration of persisted IDs now owned as core MCPs."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, AbstractSet

import mcp.installer_common as installer_common
from mcp.installer_registry import _registry_json_bytes, registry_write_transaction


def migrate_legacy_core_entries(
    *,
    path: Path,
    core_ids: AbstractSet[str],
    apply: bool = False,
) -> dict[str, Any]:
    if not isinstance(apply, bool):
        raise TypeError("apply must be a bool")
    mode = "apply" if apply else "dry_run"
    if not path.exists():
        return _report("nothing_to_migrate", mode, path, [], None)
    if not apply:
        return _plan(path, core_ids, mode)

    with registry_write_transaction(path):
        original = path.read_bytes()
        registry = _parse_registry_bytes(original)
        detected = sorted(set(registry).intersection(core_ids))
        if not detected:
            return _report("nothing_to_migrate", mode, path, [], None)

        digest = hashlib.sha256(original).hexdigest()
        backup = path.with_name(f"{path.name}.pre-core-migration-{digest}.json")
        _require_current_bytes(path, original)
        if backup.exists():
            if backup.read_bytes() != original:
                raise ValueError("Legacy-core migration backup path contains different data")
        else:
            installer_common.atomic_write_bytes(backup, original)
        _require_current_bytes(path, original)
        migrated = {name: config for name, config in registry.items() if name not in detected}
        installer_common.atomic_write_bytes(path, _registry_json_bytes(migrated))
        return _report("applied", mode, path, detected, backup)


def _plan(path: Path, core_ids: AbstractSet[str], mode: str) -> dict[str, Any]:
    registry = _parse_registry_bytes(path.read_bytes())
    detected = sorted(set(registry).intersection(core_ids))
    status = "dry_run" if detected else "nothing_to_migrate"
    return _report(status, mode, path, detected, None)


def _parse_registry_bytes(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        loaded = json.loads(text, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("Registry source status blocks legacy-core migration") from exc
    if not isinstance(loaded, dict) or not all(
        isinstance(name, str)
        and bool(name.strip())
        and isinstance(config, dict)
        for name, config in loaded.items()
    ):
        raise ValueError("Registry source status blocks legacy-core migration")
    return loaded


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_current_bytes(path: Path, expected: bytes) -> None:
    if path.read_bytes() != expected:
        raise ValueError("stale registry state; rerun migration manually")


def _report(status, mode, path, detected, backup) -> dict[str, Any]:
    return {
        "status": status,
        "mode": mode,
        "registry_path": str(path),
        "detected_core_ids": detected,
        "backup_path": str(backup) if backup is not None else None,
    }
