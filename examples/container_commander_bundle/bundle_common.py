#!/usr/bin/env python3
from datetime import datetime, timezone
import os


HOME_ROOT = "/home/trion"


MANIFEST_PATH = f"{HOME_ROOT}/.trion/home.json"


TRION_LABEL = "trion.managed"


SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/app/data/snapshots")


DEFAULT_WRITE_ROOTS = [
    f"{HOME_ROOT}/notes",
    f"{HOME_ROOT}/diary",
    f"{HOME_ROOT}/scratch",
    f"{HOME_ROOT}/workspace",
    f"{HOME_ROOT}/artifacts",
]


HOME_CAPABILITY_CLASSES = [
    "container_inventory",
    "container_inspect",
    "container_logs",
    "file_read",
    "file_list",
    "file_write",
    "file_append",
    "workspace_read",
    "workspace_write",
    "local_exec",
]


AVAILABLE_HOME_CAPABILITIES = [
    "container_inventory",
    "container_inspect",
    "container_logs",
]


def error_result(code, message, retryable=False):
    return {
        "ok": False,
        "error": {"code": code, "message": message, "retryable": retryable},
    }


def is_not_found(error):
    return error.__class__.__name__ == "NotFound"


def is_true(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def managed_flags(labels):
    managed = is_true(labels.get("trion.managed")) or "trion.blueprint" in labels
    protected = is_true(labels.get("trion.protected")) or is_true(labels.get("trion.system"))
    actions_allowed = managed and not protected
    return managed, actions_allowed, protected


def created_at(container):
    raw = getattr(container, "attrs", {}).get("Created", "")
    if raw:
        return str(raw)
    return datetime.now(timezone.utc).isoformat()


def port_rows(container):
    ports = ((container.attrs or {}).get("NetworkSettings") or {}).get("Ports") or {}
    rows = []
    for container_port, host_bindings in ports.items():
        if not host_bindings:
            rows.append({"container": str(container_port), "host": "", "ip": ""})
            continue
        for binding in host_bindings:
            rows.append(
                {
                    "container": str(container_port),
                    "host": str(binding.get("HostPort") or ""),
                    "ip": str(binding.get("HostIp") or ""),
                }
            )
    return rows


def _db_path():
    return os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")


def container_summary(container):
    labels = dict(container.labels or {})
    managed, actions_allowed, protected = managed_flags(labels)
    attrs = dict(container.attrs or {})
    image = str((attrs.get("Config") or {}).get("Image") or attrs.get("Image") or "")
    return {
        "container_id": container.id,
        "name": container.name,
        "image": image,
        "status": str(container.status or "unknown"),
        "created_at": created_at(container),
        "managed_by_trion": managed,
        "actions_allowed": actions_allowed,
        "protected": protected,
    }


def resolve_container_reference(client, container_ref):
    try:
        return client.containers.get(container_ref)
    except Exception as exc:
        if is_not_found(exc):
            containers = client.containers.list(all=True)
            for item in containers:
                if str(getattr(item, "name", "") or "").strip() == str(container_ref or "").strip():
                    return item
        raise


def action_result(container, action):
    return {"ok": True, "action": action, "container": container_summary(container)}


def guard_managed_action(container):
    summary = container_summary(container)
    if not summary["managed_by_trion"]:
        return error_result("ACTION_NOT_ALLOWED", f"Container '{summary['name']}' is not managed by TRION")
    if summary["protected"]:
        return error_result("ACTION_NOT_ALLOWED", f"Container '{summary['name']}' is protected")
    if not summary["actions_allowed"]:
        return error_result("ACTION_NOT_ALLOWED", f"Actions are not allowed for container '{summary['name']}'")
    return None
