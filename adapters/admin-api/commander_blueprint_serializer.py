from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from models import (
    Blueprint,
    HardwareIntent,
    MountDef,
    NetworkMode,
    PreStartExec,
    ResourceLimits,
    SecretRequirement,
)


def row_to_blueprint(row: sqlite3.Row) -> Blueprint:
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
            if _load("pre_start_exec_json", "{}")
            else None
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


def blueprint_to_params(bp: Blueprint) -> dict:
    return {
        "id": bp.id,
        "name": bp.name,
        "description": bp.description,
        "extends": bp.extends,
        "dockerfile": bp.dockerfile,
        "image": bp.image,
        "image_digest": bp.image_digest,
        "system_prompt": bp.system_prompt,
        "resources_json": bp.resources.model_dump_json() if bp.resources else "{}",
        "secrets_json": json.dumps([s.model_dump() for s in bp.secrets_required]),
        "mounts_json": json.dumps([m.model_dump() for m in bp.mounts]),
        "storage_scope": bp.storage_scope,
        "ports_json": json.dumps(bp.ports),
        "runtime": bp.runtime,
        "devices_json": json.dumps(bp.devices),
        "hardware_intents_json": json.dumps([i.model_dump() for i in bp.hardware_intents]),
        "environment_json": json.dumps(bp.environment),
        "healthcheck_json": json.dumps(bp.healthcheck),
        "pre_start_exec_json": bp.pre_start_exec.model_dump_json() if bp.pre_start_exec else "{}",
        "cap_add_json": json.dumps(bp.cap_add),
        "security_opt_json": json.dumps(bp.security_opt),
        "cap_drop_json": json.dumps(bp.cap_drop),
        "privileged": 1 if bp.privileged else 0,
        "read_only_rootfs": 1 if bp.read_only_rootfs else 0,
        "shm_size": bp.shm_size,
        "ipc_mode": bp.ipc_mode,
        "network": bp.network.value if bp.network else "internal",
        "tags_json": json.dumps(bp.tags),
        "exec_policy_json": json.dumps(bp.allowed_exec),
        "icon": bp.icon,
        "created_at": bp.created_at or datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
