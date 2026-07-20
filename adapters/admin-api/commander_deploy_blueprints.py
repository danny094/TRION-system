from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Optional

from models import Blueprint, HardwareIntent, MountDef, NetworkMode, PreStartExec, ResourceLimits, SecretRequirement

_INIT_LOCK = threading.Lock()
_INIT_DONE = False


def _db_path() -> str:
    return os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")


def get_conn() -> sqlite3.Connection:
    db_path = _db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_store_initialized() -> None:
    global _INIT_DONE
    if _INIT_DONE:
        return
    with _INIT_LOCK:
        if _INIT_DONE:
            return
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
        _INIT_DONE = True


def _row_to_blueprint(row: sqlite3.Row) -> Blueprint:
    def _load(key: str, default: str):
        try:
            return json.loads(row[key] or default)
        except Exception:
            return json.loads(default)

    def _str(key: str) -> str:
        try:
            return row[key] or ""
        except Exception:
            return ""

    def _bool(key: str) -> bool:
        try:
            return bool(int(row[key] or 0))
        except Exception:
            return False

    return Blueprint(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        extends=row["extends"],
        dockerfile=row["dockerfile"] or "",
        image=row["image"],
        image_digest=_str("image_digest") or None,
        system_prompt=row["system_prompt"] or "",
        resources=ResourceLimits(**_load("resources_json", "{}")),
        secrets_required=[SecretRequirement(**s) for s in _load("secrets_json", "[]")],
        mounts=[MountDef(**m) for m in _load("mounts_json", "[]")],
        storage_scope=_str("storage_scope"),
        ports=[str(p) for p in _load("ports_json", "[]") if p is not None],
        runtime=_str("runtime"),
        devices=[str(d) for d in _load("devices_json", "[]") if d is not None],
        hardware_intents=[
            HardwareIntent(**item)
            for item in _load("hardware_intents_json", "[]")
            if isinstance(item, dict)
        ],
        environment={str(k): str(v) for k, v in _load("environment_json", "{}").items()},
        healthcheck=_load("healthcheck_json", "{}"),
        pre_start_exec=(
            PreStartExec(**_load("pre_start_exec_json", "{}"))
            if _load("pre_start_exec_json", "{}") else None
        ),
        cap_add=[str(c) for c in _load("cap_add_json", "[]") if c is not None],
        security_opt=[str(o) for o in _load("security_opt_json", "[]") if o is not None],
        cap_drop=[str(c) for c in _load("cap_drop_json", "[]") if c is not None],
        privileged=_bool("privileged"),
        read_only_rootfs=_bool("read_only_rootfs"),
        shm_size=_str("shm_size"),
        ipc_mode=_str("ipc_mode"),
        network=NetworkMode(row["network"]) if row["network"] else NetworkMode.INTERNAL,
        allowed_exec=_load("exec_policy_json", "[]"),
        tags=_load("tags_json", "[]"),
        icon=row["icon"] or "📦",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_blueprint(blueprint_id: str) -> Optional[Blueprint]:
    ensure_store_initialized()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM blueprints WHERE id = ? AND (is_deleted IS NULL OR is_deleted = 0)",
            (blueprint_id,),
        ).fetchone()
        return _row_to_blueprint(row) if row else None
    finally:
        conn.close()


def list_blueprints(tag: Optional[str] = None) -> list[Blueprint]:
    ensure_store_initialized()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM blueprints WHERE (is_deleted IS NULL OR is_deleted = 0) ORDER BY name"
        ).fetchall()
        blueprints = [_row_to_blueprint(row) for row in rows]
        if tag:
            blueprints = [bp for bp in blueprints if tag.lower() in [item.lower() for item in bp.tags]]
        return blueprints
    finally:
        conn.close()


def resolve_blueprint(blueprint_id: str) -> Optional[Blueprint]:
    bp = get_blueprint(blueprint_id)
    if not bp:
        return None
    if not bp.extends:
        return bp

    parent = resolve_blueprint(bp.extends)
    if not parent:
        return bp

    merged = parent.model_copy()
    merged.id = bp.id
    merged.name = bp.name
    merged.icon = bp.icon

    if bp.description:
        merged.description = bp.description
    if bp.dockerfile:
        merged.dockerfile = bp.dockerfile
    if bp.image:
        merged.image = bp.image
    if bp.system_prompt:
        merged.system_prompt = bp.system_prompt
    if bp.storage_scope:
        merged.storage_scope = bp.storage_scope
    if bp.ports:
        merged.ports = bp.ports
    if bp.runtime:
        merged.runtime = bp.runtime
    if bp.devices:
        merged.devices = bp.devices
    if bp.environment:
        merged.environment = {**merged.environment, **bp.environment}
    if bp.healthcheck:
        merged.healthcheck = {**merged.healthcheck, **bp.healthcheck}
    if bp.pre_start_exec:
        merged.pre_start_exec = bp.pre_start_exec
    if bp.cap_add:
        merged.cap_add = bp.cap_add
    if bp.security_opt:
        merged.security_opt = bp.security_opt
    if bp.cap_drop:
        merged.cap_drop = bp.cap_drop
    if bp.privileged:
        merged.privileged = True
    if bp.read_only_rootfs:
        merged.read_only_rootfs = True
    if bp.shm_size:
        merged.shm_size = bp.shm_size
    if bp.ipc_mode:
        merged.ipc_mode = bp.ipc_mode
    if bp.network != NetworkMode.INTERNAL:
        merged.network = bp.network
    if bp.resources:
        merged.resources = bp.resources

    if bp.hardware_intents:
        child_keys = {
            (i.resource_id, i.target_type, i.target_id, i.attachment_mode)
            for i in bp.hardware_intents
        }
        merged.hardware_intents = [
            i
            for i in merged.hardware_intents
            if (i.resource_id, i.target_type, i.target_id, i.attachment_mode) not in child_keys
        ]
        merged.hardware_intents.extend(bp.hardware_intents)

    merged.tags = list(set(parent.tags + bp.tags))

    existing_secret_names = {s.name for s in parent.secrets_required}
    for secret in bp.secrets_required:
        if secret.name not in existing_secret_names:
            merged.secrets_required.append(secret)

    existing_mounts = {mount.container for mount in parent.mounts}
    for mount in bp.mounts:
        if mount.container not in existing_mounts:
            merged.mounts.append(mount)

    merged.created_at = bp.created_at
    merged.updated_at = bp.updated_at
    return merged
