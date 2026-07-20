from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from commander_deploy_blueprints import ensure_store_initialized, get_blueprint, get_conn
from commander_runtime_models import NetworkMode

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_text(value: Any, default: Any) -> str:
    return json.dumps(value if value is not None else default)


def _detail(blueprint) -> dict[str, Any]:
    definition = blueprint.model_dump() if hasattr(blueprint, "model_dump") else dict(blueprint or {})
    return {
        "blueprint_id": str(getattr(blueprint, "id", "") or definition.get("id") or ""),
        "name": str(getattr(blueprint, "name", "") or definition.get("name") or ""),
        "description": str(getattr(blueprint, "description", "") or definition.get("description") or ""),
        "version": str(getattr(blueprint, "updated_at", "") or getattr(blueprint, "created_at", "") or ""),
        "definition": definition,
    }


def _trust(detail: dict[str, Any]) -> dict[str, Any]:
    image_ref = str((detail.get("definition") or {}).get("image") or "").strip()
    trusted = image_ref.startswith(("python:", "node:", "postgres:", "nginx:", "redis:", "josh5/steam-headless"))
    return {
        "level": "verified" if trusted else "unverified",
        "source": "trusted-image-pattern" if trusted else "user-created",
        "image_ref": image_ref,
    }


def _normalize(data: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    definition = dict(existing.get("definition") or {})
    definition.update({k: v for k, v in dict(data or {}).items() if v is not None})
    blueprint_id = str(data.get("id") or existing.get("blueprint_id") or definition.get("id") or "").strip()
    name = str(data.get("name") or existing.get("name") or definition.get("name") or "").strip()
    if not blueprint_id or not name:
        raise ValueError("id and name are required")
    created_at = str(existing.get("version") or existing.get("created_at") or _now()).strip() or _now()
    return {
        "id": blueprint_id,
        "name": name,
        "description": str(definition.get("description") or ""),
        "extends": definition.get("extends"),
        "dockerfile": str(definition.get("dockerfile") or ""),
        "image": definition.get("image"),
        "image_digest": definition.get("image_digest"),
        "system_prompt": str(definition.get("system_prompt") or ""),
        "resources_json": _json_text(definition.get("resources"), {}),
        "secrets_json": _json_text(definition.get("secrets_required"), []),
        "mounts_json": _json_text(definition.get("mounts"), []),
        "storage_scope": str(definition.get("storage_scope") or ""),
        "ports_json": _json_text(definition.get("ports"), []),
        "runtime": str(definition.get("runtime") or ""),
        "devices_json": _json_text(definition.get("devices"), []),
        "hardware_intents_json": _json_text(definition.get("hardware_intents"), []),
        "environment_json": _json_text(definition.get("environment"), {}),
        "healthcheck_json": _json_text(definition.get("healthcheck"), {}),
        "pre_start_exec_json": _json_text(definition.get("pre_start_exec"), {}),
        "cap_add_json": _json_text(definition.get("cap_add"), []),
        "security_opt_json": _json_text(definition.get("security_opt"), []),
        "cap_drop_json": _json_text(definition.get("cap_drop"), []),
        "privileged": 1 if bool(definition.get("privileged")) else 0,
        "read_only_rootfs": 1 if bool(definition.get("read_only_rootfs")) else 0,
        "shm_size": str(definition.get("shm_size") or ""),
        "ipc_mode": str(definition.get("ipc_mode") or ""),
        "network": str(definition.get("network") or NetworkMode.INTERNAL.value),
        "tags_json": _json_text(definition.get("tags"), []),
        "exec_policy_json": _json_text(definition.get("allowed_exec"), []),
        "icon": str(definition.get("icon") or "📦"),
        "created_at": created_at,
        "updated_at": _now(),
    }


def _parse_simple_yaml(yaml_content: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in yaml_content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"unsupported yaml line: {raw_line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            raise ValueError(f"missing key in yaml line: {raw_line}")
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
    return data


def _yaml_load(yaml_content: str) -> dict[str, Any]:
    if yaml is not None:
        data = yaml.safe_load(yaml_content) or {}
    else:
        data = _parse_simple_yaml(yaml_content)
    if not isinstance(data, dict):
        raise ValueError("yaml must describe an object")
    return data


def _yaml_dump(data: dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
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


def create_blueprint(definition: dict[str, Any]) -> dict[str, Any]:
    ensure_store_initialized()
    params = _normalize(definition)
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO blueprints (
                id, name, description, extends, dockerfile, image, image_digest, system_prompt,
                resources_json, secrets_json, mounts_json, storage_scope, ports_json, runtime,
                devices_json, hardware_intents_json, environment_json, healthcheck_json,
                pre_start_exec_json, cap_add_json, security_opt_json, cap_drop_json, privileged,
                read_only_rootfs, shm_size, ipc_mode, network, tags_json, exec_policy_json,
                icon, created_at, updated_at, is_deleted
            ) VALUES (
                :id, :name, :description, :extends, :dockerfile, :image, :image_digest, :system_prompt,
                :resources_json, :secrets_json, :mounts_json, :storage_scope, :ports_json, :runtime,
                :devices_json, :hardware_intents_json, :environment_json, :healthcheck_json,
                :pre_start_exec_json, :cap_add_json, :security_opt_json, :cap_drop_json, :privileged,
                :read_only_rootfs, :shm_size, :ipc_mode, :network, :tags_json, :exec_policy_json,
                :icon, :created_at, :updated_at, 0
            )
            """,
            params,
        )
        conn.commit()
    finally:
        conn.close()

    blueprint = get_blueprint(params["id"])
    detail = _detail(blueprint) if blueprint else {}
    return {"created": True, "blueprint": detail, "trust": _trust(detail)}


def update_blueprint(blueprint_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    existing = get_blueprint(blueprint_id)
    if not existing:
        return {"error": f"Blueprint '{blueprint_id}' not found"}
    params = _normalize(updates, existing=_detail(existing))
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE blueprints SET
                name=:name, description=:description, extends=:extends, dockerfile=:dockerfile,
                image=:image, image_digest=:image_digest, system_prompt=:system_prompt,
                resources_json=:resources_json, secrets_json=:secrets_json, mounts_json=:mounts_json,
                storage_scope=:storage_scope, ports_json=:ports_json, runtime=:runtime,
                devices_json=:devices_json, hardware_intents_json=:hardware_intents_json,
                environment_json=:environment_json, healthcheck_json=:healthcheck_json,
                pre_start_exec_json=:pre_start_exec_json, cap_add_json=:cap_add_json,
                security_opt_json=:security_opt_json, cap_drop_json=:cap_drop_json,
                privileged=:privileged, read_only_rootfs=:read_only_rootfs, shm_size=:shm_size,
                ipc_mode=:ipc_mode, network=:network, tags_json=:tags_json,
                exec_policy_json=:exec_policy_json, icon=:icon, updated_at=:updated_at
            WHERE id=:id
            """,
            params,
        )
        conn.commit()
    finally:
        conn.close()

    blueprint = get_blueprint(blueprint_id)
    detail = _detail(blueprint) if blueprint else {}
    return {"updated": True, "blueprint": detail, "trust": _trust(detail)}


def delete_blueprint(blueprint_id: str) -> dict[str, Any]:
    ensure_store_initialized()
    conn = get_conn()
    try:
        cursor = conn.execute("UPDATE blueprints SET is_deleted = 1, updated_at = ? WHERE id = ?", (_now(), blueprint_id))
        conn.commit()
        return {"deleted": bool(cursor.rowcount), "blueprint_id": blueprint_id}
    finally:
        conn.close()


def import_blueprint_yaml(yaml_content: str) -> dict[str, Any]:
    data = _yaml_load(yaml_content)
    return create_blueprint(data)


def export_blueprint_yaml(blueprint_id: str) -> dict[str, Any]:
    blueprint = get_blueprint(blueprint_id)
    if not blueprint:
        return {"error": f"Blueprint '{blueprint_id}' not found"}
    detail = _detail(blueprint)
    return {"blueprint_id": blueprint_id, "yaml": _yaml_dump(detail.get("definition") or {})}
