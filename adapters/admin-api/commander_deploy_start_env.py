from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from commander_host_companion_runtime import (
    ensure_host_companion,
    ensure_package_storage_scope,
    get_package_manifest,
)
from commander_package_runtime_views import apply_package_runtime_views
from commander_secret_store import get_secret_value, get_secrets_for_blueprint, log_secret_access
from models import Blueprint, SecretScope


def setup_host_companion(blueprint_id: str, bp: Blueprint) -> Optional[Dict[str, Any]]:
    try:
        package_manifest = get_package_manifest(blueprint_id)
        if isinstance(package_manifest, dict) and package_manifest.get("host_companion"):
            hc = package_manifest["host_companion"] if isinstance(package_manifest["host_companion"], dict) else {}
            mode = str(hc.get("mode", "materialize") or "materialize").strip().lower()
            if mode not in {"discovery_only", "readonly", "read_only"}:
                ensure_host_companion(blueprint_id, overwrite=False)
        if isinstance(package_manifest, dict):
            ensure_package_storage_scope(blueprint_id, blueprint=bp, manifest=package_manifest)
        return package_manifest if isinstance(package_manifest, dict) else None
    except Exception as exc:
        raise RuntimeError(f"host_companion_setup_failed: {blueprint_id}: {exc}") from exc


def build_env_vars(
    bp: Blueprint,
    blueprint_id: str,
    extra_env: Optional[Dict[str, str]],
) -> Dict[str, str]:
    env_vars: Dict[str, str] = {}
    for key, value in dict(bp.environment or {}).items():
        env_name, env_value = str(key), str(value)
        if env_value.startswith("vault://"):
            secret_name = env_value[len("vault://") :].strip()
            if not secret_name:
                raise RuntimeError(f"invalid_vault_ref: empty secret reference for env '{env_name}'")
            secret_value = get_secret_value(secret_name, SecretScope.BLUEPRINT, blueprint_id)
            if secret_value is None:
                secret_value = get_secret_value(secret_name, SecretScope.GLOBAL)
            if secret_value is None:
                raise RuntimeError(f"vault_ref_not_found: '{secret_name}' for env '{env_name}' in blueprint '{blueprint_id}'")
            env_vars[env_name] = secret_value
            log_secret_access(secret_name, "inject_vault_ref", "", blueprint_id)
        else:
            env_vars[env_name] = env_value
    if bp.secrets_required:
        secret_env = get_secrets_for_blueprint(blueprint_id, [s.model_dump() for s in bp.secrets_required])
        env_vars.update(secret_env)
        for name in secret_env:
            log_secret_access(name, "inject", "", blueprint_id)
    if extra_env:
        env_vars.update(extra_env)
    return env_vars


def prepare_runtime_blueprint(
    bp: Blueprint,
    mount_overrides: Optional[List[Dict[str, Any]]],
    device_overrides: Optional[List[str]],
    storage_scope_override: Optional[str],
    *,
    normalize_mounts: Callable,
    normalize_devices: Callable,
    compose_runtime_blueprint: Callable,
    validate_blueprint_mounts: Callable,
    ensure_bind_mount_host_dirs: Callable,
    runtime_mount_payloads: Callable,
    runtime_mount_asset_ids: Callable,
) -> Tuple[Blueprint, List[Any], List[str], List[dict], List[str], str]:
    runtime_mounts = normalize_mounts(mount_overrides)
    runtime_devices = normalize_devices(device_overrides)
    scope_override = str(storage_scope_override or "").strip()
    force_auto_scope = scope_override.lower() in {"__auto__", "auto"}
    asset_backed = any(str(getattr(m, "asset_id", "") or "").strip() for m in list(runtime_mounts or []))
    if asset_backed and not scope_override:
        force_auto_scope = True
    if force_auto_scope:
        scope_override = ""
    if runtime_mounts or runtime_devices or scope_override:
        bp = compose_runtime_blueprint(
            bp,
            runtime_mount_overrides=runtime_mounts,
            runtime_device_overrides=runtime_devices,
            storage_scope_override=scope_override,
            force_auto_scope=force_auto_scope,
        )
    mounts_ok, mounts_reason = validate_blueprint_mounts(bp)
    if not mounts_ok:
        raise RuntimeError(mounts_reason)
    ensure_bind_mount_host_dirs(bp.mounts)
    mount_payloads = runtime_mount_payloads(runtime_mounts)
    asset_ids = runtime_mount_asset_ids(runtime_mounts)
    effective_scope = str(getattr(bp, "storage_scope", "") or "").strip()
    return bp, runtime_mounts, runtime_devices, mount_payloads, asset_ids, effective_scope
