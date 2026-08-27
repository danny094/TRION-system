#!/usr/bin/env python3
import json
import os
import sqlite3

from bundle_common import _db_path, error_result


def get_conn():
    db_path = _db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_store_initialized():
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blueprints (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                extends TEXT,
                dockerfile TEXT DEFAULT '',
                image TEXT,
                image_digest TEXT,
                system_prompt TEXT DEFAULT '',
                resources_json TEXT DEFAULT '{}',
                secrets_json TEXT DEFAULT '[]',
                mounts_json TEXT DEFAULT '[]',
                storage_scope TEXT DEFAULT '',
                ports_json TEXT DEFAULT '[]',
                runtime TEXT DEFAULT '',
                devices_json TEXT DEFAULT '[]',
                hardware_intents_json TEXT DEFAULT '[]',
                environment_json TEXT DEFAULT '{}',
                healthcheck_json TEXT DEFAULT '{}',
                pre_start_exec_json TEXT DEFAULT '{}',
                cap_add_json TEXT DEFAULT '[]',
                security_opt_json TEXT DEFAULT '[]',
                cap_drop_json TEXT DEFAULT '[]',
                privileged INTEGER DEFAULT 0,
                read_only_rootfs INTEGER DEFAULT 0,
                shm_size TEXT DEFAULT '',
                ipc_mode TEXT DEFAULT '',
                network TEXT DEFAULT 'internal',
                tags_json TEXT DEFAULT '[]',
                exec_policy_json TEXT DEFAULT '[]',
                icon TEXT DEFAULT '📦',
                created_at TEXT,
                updated_at TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def load_json(row, key, default):
    try:
        return json.loads(row[key] or json.dumps(default))
    except Exception:
        return default


def row_value(row, key, default=""):
    try:
        value = row[key]
    except Exception:
        return default
    return default if value is None else value


def row_version(row):
    updated = str(row["updated_at"] or "").strip()
    created = str(row["created_at"] or "").strip()
    return updated or created


def blueprint_definition(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "extends": row_value(row, "extends", ""),
        "dockerfile": row["dockerfile"] or "",
        "image": row["image"] or "",
        "image_digest": row_value(row, "image_digest", ""),
        "system_prompt": row_value(row, "system_prompt", ""),
        "runtime": row["runtime"] or "",
        "ports": load_json(row, "ports_json", []),
        "mounts": load_json(row, "mounts_json", []),
        "environment": load_json(row, "environment_json", {}),
        "resources": load_json(row, "resources_json", {}),
        "secrets_required": load_json(row, "secrets_json", []),
        "storage_scope": row_value(row, "storage_scope", ""),
        "devices": load_json(row, "devices_json", []),
        "hardware_intents": load_json(row, "hardware_intents_json", []),
        "healthcheck": load_json(row, "healthcheck_json", {}),
        "pre_start_exec": load_json(row, "pre_start_exec_json", {}),
        "cap_add": load_json(row, "cap_add_json", []),
        "security_opt": load_json(row, "security_opt_json", []),
        "cap_drop": load_json(row, "cap_drop_json", []),
        "privileged": bool(row_value(row, "privileged", 0)),
        "read_only_rootfs": bool(row_value(row, "read_only_rootfs", 0)),
        "shm_size": row_value(row, "shm_size", ""),
        "ipc_mode": row_value(row, "ipc_mode", ""),
        "network": row_value(row, "network", "internal"),
        "allowed_exec": load_json(row, "exec_policy_json", []),
        "tags": load_json(row, "tags_json", []),
        "icon": row["icon"] or "📦",
    }


def list_blueprints():
    try:
        ensure_store_initialized()
        conn = get_conn()
        rows = conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM blueprints "
            "WHERE (is_deleted IS NULL OR is_deleted = 0) ORDER BY name"
        ).fetchall()
        conn.close()
        return {
            "blueprints": [
                {
                    "blueprint_id": row["id"],
                    "name": row["name"],
                    "description": row["description"] or "",
                    "version": row_version(row),
                }
                for row in rows
            ]
        }
    except sqlite3.OperationalError:
        return {"blueprints": []}


def get_blueprint(blueprint_id):
    try:
        ensure_store_initialized()
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM blueprints WHERE id = ? AND (is_deleted IS NULL OR is_deleted = 0)",
            (blueprint_id,),
        ).fetchone()
        conn.close()
        if not row:
            return error_result("BLUEPRINT_NOT_FOUND", f"Blueprint '{blueprint_id}' not found")
        return {
            "blueprint": {
                "blueprint_id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "version": row_version(row),
                "definition": blueprint_definition(row),
            }
        }
    except sqlite3.OperationalError:
        return error_result("RUNTIME_UNAVAILABLE", "Blueprint store is not initialized", retryable=True)
