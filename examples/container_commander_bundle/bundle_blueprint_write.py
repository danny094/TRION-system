#!/usr/bin/env python3
from datetime import datetime, timezone

import bundle_blueprint_store
from bundle_blueprint_store import ensure_store_initialized, get_conn
from bundle_common import error_result
from bundle_yaml import json_text, yaml_dump, yaml_load


def normalize_blueprint(data, existing=None):
    existing = existing or {}
    definition = dict(existing.get("definition") or {})
    definition.update({k: v for k, v in data.items() if v is not None})
    blueprint_id = str(data.get("id") or existing.get("blueprint_id") or definition.get("id") or "").strip()
    name = str(data.get("name") or existing.get("name") or definition.get("name") or "").strip()
    if not blueprint_id or not name:
        raise ValueError("id and name are required")
    created = str(existing.get("version") or existing.get("created_at") or datetime.now(timezone.utc).isoformat()).strip()
    return {
        "id": blueprint_id,
        "name": name,
        "description": str(definition.get("description") or ""),
        "extends": definition.get("extends"),
        "dockerfile": str(definition.get("dockerfile") or ""),
        "image": definition.get("image"),
        "image_digest": definition.get("image_digest"),
        "system_prompt": str(definition.get("system_prompt") or ""),
        "resources_json": json_text(definition.get("resources"), {}),
        "secrets_json": json_text(definition.get("secrets_required"), []),
        "mounts_json": json_text(definition.get("mounts"), []),
        "storage_scope": str(definition.get("storage_scope") or ""),
        "ports_json": json_text(definition.get("ports"), []),
        "runtime": str(definition.get("runtime") or ""),
        "devices_json": json_text(definition.get("devices"), []),
        "hardware_intents_json": json_text(definition.get("hardware_intents"), []),
        "environment_json": json_text(definition.get("environment"), {}),
        "healthcheck_json": json_text(definition.get("healthcheck"), {}),
        "pre_start_exec_json": json_text(definition.get("pre_start_exec"), {}),
        "cap_add_json": json_text(definition.get("cap_add"), []),
        "security_opt_json": json_text(definition.get("security_opt"), []),
        "cap_drop_json": json_text(definition.get("cap_drop"), []),
        "privileged": 1 if bool(definition.get("privileged")) else 0,
        "read_only_rootfs": 1 if bool(definition.get("read_only_rootfs")) else 0,
        "shm_size": str(definition.get("shm_size") or ""),
        "ipc_mode": str(definition.get("ipc_mode") or ""),
        "network": str(definition.get("network") or "internal"),
        "tags_json": json_text(definition.get("tags"), []),
        "exec_policy_json": json_text(definition.get("allowed_exec"), []),
        "icon": str(definition.get("icon") or "📦"),
        "created_at": created or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def blueprint_trust(detail):
    image_ref = str((detail.get("definition") or {}).get("image") or "").strip()
    trusted = image_ref.startswith(("python:", "node:", "postgres:", "nginx:", "redis:", "josh5/steam-headless"))
    return {
        "level": "verified" if trusted else "unverified",
        "source": "trusted-image-pattern" if trusted else "user-created",
        "image_ref": image_ref,
    }


def create_blueprint(blueprint):
    ensure_store_initialized()
    try:
        params = normalize_blueprint(blueprint)
    except Exception as exc:
        return error_result("BLUEPRINT_CREATE_FAILED", str(exc))
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
    except Exception as exc:
        return error_result("BLUEPRINT_CREATE_FAILED", str(exc))
    finally:
        conn.close()
    detail = bundle_blueprint_store.get_blueprint(params["id"]).get("blueprint", {})
    return {"created": True, "blueprint": detail, "trust": blueprint_trust(detail)}


def update_blueprint(blueprint_id, updates):
    existing = bundle_blueprint_store.get_blueprint(blueprint_id).get("blueprint")
    if not isinstance(existing, dict):
        return error_result("BLUEPRINT_NOT_FOUND", f"Blueprint '{blueprint_id}' not found")
    try:
        params = normalize_blueprint(updates, existing=existing)
    except Exception as exc:
        return error_result("BLUEPRINT_UPDATE_FAILED", str(exc))
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
    except Exception as exc:
        return error_result("BLUEPRINT_UPDATE_FAILED", str(exc))
    finally:
        conn.close()
    detail = bundle_blueprint_store.get_blueprint(blueprint_id).get("blueprint", {})
    return {"updated": True, "blueprint": detail, "trust": blueprint_trust(detail)}


def delete_blueprint(blueprint_id):
    ensure_store_initialized()
    conn = get_conn()
    try:
        cursor = conn.execute(
            "UPDATE blueprints SET is_deleted = 1, updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), blueprint_id),
        )
        conn.commit()
        return {"deleted": bool(cursor.rowcount), "blueprint_id": blueprint_id}
    finally:
        conn.close()


def import_blueprint_yaml(yaml_content):
    try:
        data = yaml_load(yaml_content)
    except Exception as exc:
        return error_result("BLUEPRINT_IMPORT_FAILED", str(exc))
    return create_blueprint(data)


def export_blueprint_yaml(blueprint_id):
    detail = bundle_blueprint_store.get_blueprint(blueprint_id).get("blueprint")
    if not isinstance(detail, dict):
        return error_result("BLUEPRINT_NOT_FOUND", f"Blueprint '{blueprint_id}' not found")
    return {"blueprint_id": blueprint_id, "yaml": yaml_dump(detail.get("definition") or {})}
