#!/usr/bin/env python3
import importlib.util
import io
import json
import os
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path


def _load_local_module(name: str, filename: str):
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"container_commander_bundle_{name}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed_to_load_{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_proxy_views = _load_local_module("proxy_views", "proxy_views.py")
ensure_proxy_running = _proxy_views.ensure_proxy_running
get_whitelist = _proxy_views.get_whitelist
set_whitelist = _proxy_views.set_whitelist
stop_proxy = _proxy_views.stop_proxy

_dashboard_views = _load_local_module("dashboard_views", "dashboard_views.py")
get_dashboard_overview = _dashboard_views.get_dashboard_overview
_host_companion_views = _load_local_module("host_companion_views", "host_companion_views.py")
check_host_companion = _host_companion_views.check_host_companion
repair_host_companion = _host_companion_views.repair_host_companion
uninstall_host_companion = _host_companion_views.uninstall_host_companion
get_package_manifest = _host_companion_views.get_package_manifest
_marketplace_views = _load_local_module("marketplace_views", "marketplace_views.py")
get_starters = _marketplace_views.get_starters
list_bundles = _marketplace_views.list_bundles
list_catalog = _marketplace_views.list_catalog
sync_remote_catalog = _marketplace_views.sync_remote_catalog
_marketplace_mutations = _load_local_module("marketplace_mutations", "marketplace_mutations.py")
install_starter = _marketplace_mutations.install_starter
install_catalog_blueprint = _marketplace_mutations.install_catalog_blueprint
export_bundle = _marketplace_mutations.export_bundle
import_bundle = _marketplace_mutations.import_bundle

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None


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

TOOLS = [
    {
        "name": "container_list",
        "description": "List containers with stable v2 status fields.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "container_inspect",
        "description": "Inspect one container with stable v2 detail fields including blueprint_id and home_scope.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "container_logs",
        "description": "Read bounded logs from one container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
                "tail": {"type": "integer", "default": 200},
                "since": {"type": "string", "default": ""},
                "limit_chars": {"type": "integer", "default": 16000},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "container_stats",
        "description": "Read live resource stats + efficiency score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "runtime_quota",
        "description": "Read runtime session quota limits and current managed usage.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "container_exec",
        "description": "Execute one bounded command inside a running container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 30},
            },
            "anyOf": [{"required": ["container_id", "command"]}, {"required": ["container_name", "command"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "container_exec_detailed",
        "description": "Execute one bounded command and return split stdout/stderr details.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 30},
            },
            "anyOf": [{"required": ["container_id", "command"]}, {"required": ["container_name", "command"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "runtime_cleanup_all",
        "description": "Stop and remove all TRION-managed containers.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "remove_stopped_container",
        "description": "Remove one stopped TRION-managed container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "network_list",
        "description": "List TRION-managed Docker networks.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "network_info",
        "description": "Get network details for a specific container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "network_cleanup",
        "description": "Remove empty isolated TRION-managed networks.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "proxy_start",
        "description": "Enable the commander proxy policy surface.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "proxy_stop",
        "description": "Disable the commander proxy policy surface.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "proxy_whitelist_get",
        "description": "Read the allowed outbound domains for one blueprint.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "proxy_whitelist_set",
        "description": "Store the allowed outbound domains for one blueprint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "blueprint_id": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["blueprint_id", "domains"],
            "additionalProperties": False,
        },
    },
    {
        "name": "dashboard_overview",
        "description": "Aggregate commander runtime inventory into a dashboard-shaped read model.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "host_companion_check",
        "description": "Inspect host-companion/package manifest status for one blueprint.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "host_companion_repair",
        "description": "Attempt host-companion repair for one blueprint.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "host_companion_uninstall",
        "description": "Attempt host-companion uninstall for one blueprint.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "package_manifest_get",
        "description": "Read the local package manifest for one blueprint if present.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "marketplace_bundle_list",
        "description": "List exported marketplace bundles from the commander marketplace directory.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "marketplace_starter_list",
        "description": "List built-in starter blueprints.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "marketplace_catalog_list",
        "description": "List cached catalog entries, optionally filtered by category and trust.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "trusted_only": {"type": "boolean", "default": False}
            },
            "additionalProperties": False
        },
    },
    {
        "name": "marketplace_catalog_sync",
        "description": "Refresh the remote blueprint catalog cache from a GitHub-backed index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_url": {"type": "string"},
                "branch": {"type": "string", "default": "main"}
            },
            "additionalProperties": False
        },
    },
    {
        "name": "marketplace_starter_install",
        "description": "Install one built-in starter blueprint into the commander store.",
        "inputSchema": {
            "type": "object",
            "properties": {"starter_id": {"type": "string"}},
            "required": ["starter_id"],
            "additionalProperties": False
        },
    },
    {
        "name": "marketplace_catalog_install",
        "description": "Install one blueprint from the cached remote catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "blueprint_id": {"type": "string"},
                "overwrite": {"type": "boolean", "default": False}
            },
            "required": ["blueprint_id"],
            "additionalProperties": False
        },
    },
    {
        "name": "marketplace_bundle_export",
        "description": "Export one blueprint as a shareable TRION bundle.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False
        },
    },
    {
        "name": "marketplace_bundle_import",
        "description": "Import one TRION bundle from base64-encoded archive bytes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bundle_bytes_b64": {"type": "string"},
                "filename": {"type": "string"},
                "overwrite": {"type": "boolean", "default": False}
            },
            "required": ["bundle_bytes_b64"],
            "additionalProperties": False
        },
    },
    {
        "name": "volume_list",
        "description": "List TRION-managed workspace volumes.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "volume_get",
        "description": "Get one volume with snapshot metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {"volume_name": {"type": "string"}},
            "required": ["volume_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "volume_remove",
        "description": "Remove one workspace volume.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string"},
                "force": {"type": "boolean", "default": False}
            },
            "required": ["volume_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "volume_cleanup",
        "description": "Find and optionally remove orphaned workspace volumes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {"type": "boolean", "default": True}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "snapshot_list",
        "description": "List snapshots, optionally filtered by volume prefix.",
        "inputSchema": {
            "type": "object",
            "properties": {"volume_name": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "snapshot_delete",
        "description": "Delete one stored snapshot tarball.",
        "inputSchema": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
            "additionalProperties": False,
        },
    },
    {
        "name": "snapshot_create",
        "description": "Create one snapshot tarball for a workspace volume.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string"},
                "tag": {"type": "string", "default": ""}
            },
            "required": ["volume_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "snapshot_restore",
        "description": "Restore one snapshot tarball into a target or derived volume.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "target_volume": {"type": "string", "default": ""}
            },
            "required": ["filename"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blueprint_list",
        "description": "List installed blueprints from the commander store.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "blueprint_get",
        "description": "Get one blueprint with a stable v2 detail shape.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blueprint_create",
        "description": "Create one blueprint in the commander store.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint": {"type": "object"}},
            "required": ["blueprint"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blueprint_update",
        "description": "Update one blueprint in the commander store.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "blueprint_id": {"type": "string"},
                "updates": {"type": "object"},
            },
            "required": ["blueprint_id", "updates"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blueprint_delete",
        "description": "Soft-delete one blueprint in the commander store.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blueprint_import_yaml",
        "description": "Import one blueprint from YAML.",
        "inputSchema": {
            "type": "object",
            "properties": {"yaml": {"type": "string"}},
            "required": ["yaml"],
            "additionalProperties": False,
        },
    },
    {
        "name": "blueprint_export_yaml",
        "description": "Export one blueprint as YAML.",
        "inputSchema": {
            "type": "object",
            "properties": {"blueprint_id": {"type": "string"}},
            "required": ["blueprint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "start_stopped_container",
        "description": "Start a stopped TRION-managed container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "stop_container",
        "description": "Stop a running TRION-managed container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "container_name": {"type": "string"},
            },
            "anyOf": [{"required": ["container_id"]}, {"required": ["container_name"]}],
            "additionalProperties": False,
        },
    },
]


def error_result(code, message, retryable=False):
    return {
        "ok": False,
        "error": {"code": code, "message": message, "retryable": retryable},
    }


def get_docker_client():
    try:
        from docker import from_env

        return from_env()
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def is_not_found(error):
    return error.__class__.__name__ == "NotFound"


def is_true(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


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
    image = getattr(getattr(container, "image", None), "tags", None) or []
    return {
        "container_id": container.id,
        "name": container.name,
        "image": image[0] if image else str((container.attrs or {}).get("Config", {}).get("Image") or ""),
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


def list_containers():
    try:
        client = get_docker_client()
        containers = client.containers.list(all=True)
        return {"containers": [container_summary(container) for container in containers]}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def inspect_container(container_id):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_id)
        summary = container_summary(container)
        labels = dict(container.labels or {})
        manifest = read_home_manifest(container)
        return {
            "container": {
                **summary,
                "blueprint_id": blueprint_id_from_labels(labels),
                "labels": labels,
                "ports": port_rows(container),
                "mounts": [
                    f"{mount.get('Source', '?')}:{mount.get('Destination', '?')}"
                    for mount in (container.attrs or {}).get("Mounts", [])
                ],
                "runtime_state": dict((container.attrs or {}).get("State") or {}),
                "home_scope": build_home_scope(labels, manifest),
            }
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_logs(container_id, tail=200, since="", limit_chars=16000):
    safe_tail = max(1, min(int(tail), 500))
    safe_limit = max(256, min(int(limit_chars), 64000))
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_id)
        raw = container.logs(tail=safe_tail, timestamps=True, since=since or None)
        logs = raw.decode("utf-8", errors="replace")
        truncated = len(logs) > safe_limit
        if truncated:
            logs = logs[-safe_limit:]
        return {
            "container_id": container_id,
            "logs": logs,
            "truncated": truncated,
            "tail": safe_tail,
            "since": str(since or ""),
            "limit_chars": safe_limit,
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_stats(container_id):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_id)
        attrs = container.attrs or {}
        stats = container.stats(stream=False)
        network_settings = attrs.get("NetworkSettings", {}) or {}
        networks = network_settings.get("Networks", {}) or {}
        ip_address = next((str(v.get("IPAddress") or "") for v in networks.values() if v.get("IPAddress")), "")

        cpu_stats = dict(stats.get("cpu_stats") or {})
        precpu_stats = dict(stats.get("precpu_stats") or {})
        cpu_usage = dict(cpu_stats.get("cpu_usage") or {})
        precpu_usage = dict(precpu_stats.get("cpu_usage") or {})
        cpu_delta = float(cpu_usage.get("total_usage", 0) or 0) - float(precpu_usage.get("total_usage", 0) or 0)
        system_delta = float(cpu_stats.get("system_cpu_usage", 0) or 0) - float(precpu_stats.get("system_cpu_usage", 0) or 0)
        num_cpus = int(cpu_stats.get("online_cpus", 1) or 1)
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0

        memory_stats = dict(stats.get("memory_stats") or {})
        mem_usage = float(memory_stats.get("usage", 0) or 0)
        mem_limit = float(memory_stats.get("limit", 0) or 0)
        mem_mb = mem_usage / (1024 * 1024)
        mem_limit_mb = mem_limit / (1024 * 1024) if mem_limit > 0 else 0.0

        net_stats = dict(stats.get("networks") or {})
        net_rx = sum(int((values or {}).get("rx_bytes", 0) or 0) for values in net_stats.values())
        net_tx = sum(int((values or {}).get("tx_bytes", 0) or 0) for values in net_stats.values())

        score = 1.0
        if cpu_percent < 1.0:
            score -= 0.3
        elif cpu_percent < 5.0:
            score -= 0.1
        mem_pct = ((mem_mb / mem_limit_mb) * 100.0) if mem_limit_mb > 0 else 0.0
        if mem_pct > 80 and cpu_percent < 2.0:
            score -= 0.2
        score = max(0.0, min(1.0, score))
        level = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"

        return {
            "container_id": container_id,
            "cpu_percent": round(cpu_percent, 1),
            "memory_mb": round(mem_mb, 1),
            "memory_limit_mb": round(mem_limit_mb, 1),
            "network_rx_bytes": net_rx,
            "network_tx_bytes": net_tx,
            "ip_address": ip_address,
            "ports": port_rows(container),
            "efficiency": {"score": round(score, 2), "level": level},
            "deploy_warnings": [],
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def runtime_quota():
    try:
        env_mem = os.environ.get("COMMANDER_MAX_MEMORY_MB", "").strip()
        env_cpu = os.environ.get("COMMANDER_MAX_CPU", "").strip()
        env_containers = os.environ.get("COMMANDER_MAX_CONTAINERS", "").strip()

        if env_mem:
            max_mem_mb = max(512, int(env_mem))
        else:
            try:
                with open("/proc/meminfo", encoding="utf-8") as meminfo:
                    for line in meminfo:
                        if line.startswith("MemTotal:"):
                            max_mem_mb = max(2048, int(line.split()[1]) // 1024 - 4096)
                            break
                    else:
                        max_mem_mb = 2048
            except Exception:
                max_mem_mb = 2048

        max_cpu = max(0.5, float(env_cpu)) if env_cpu else max(2.0, float(os.cpu_count() or 2) - 2.0)
        max_containers = int(env_containers) if env_containers else 5

        client = get_docker_client()
        containers = client.containers.list(all=True)
        managed = [container for container in containers if managed_flags(dict(getattr(container, "labels", {}) or {}))[0]]

        memory_used_mb = 0
        cpu_used = 0.0
        for container in managed:
            host_cfg = ((container.attrs or {}).get("HostConfig") or {})
            memory_used_mb += int(float(host_cfg.get("Memory", 0) or 0) / (1024 * 1024))
            cpu_used += float(host_cfg.get("NanoCpus", 0) or 0) / 1e9

        return {
            "max_containers": int(max_containers),
            "max_total_memory_mb": int(max_mem_mb),
            "max_total_cpu": float(max_cpu),
            "containers_used": len(managed),
            "memory_used_mb": int(memory_used_mb),
            "cpu_used": round(cpu_used, 2),
        }
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


MAX_EXEC_OUTPUT = 8000
EXEC_TIMEOUT_EXIT_CODE = 124
EXEC_TIMEOUT_MARKER = "__TRION_EXEC_TIMEOUT__"


def _allowed_exec(blueprint_id):
    detail = get_blueprint(blueprint_id)
    if not isinstance(detail, dict) or bool(detail.get("ok") is False):
        return []
    blueprint = detail.get("blueprint")
    if not isinstance(blueprint, dict):
        return []
    definition = blueprint.get("definition")
    if not isinstance(definition, dict):
        return []
    values = definition.get("allowed_exec")
    return [str(item).strip() for item in list(values or []) if str(item).strip()]


def _check_exec_policy(container, command):
    blueprint_id = str((container.labels or {}).get("trion.blueprint") or "").strip()
    if not blueprint_id:
        return None
    allowed = _allowed_exec(blueprint_id)
    if not allowed:
        return None
    cmd_prefix = command.strip().split()[0] if str(command or "").strip() else ""
    if cmd_prefix not in allowed:
        return error_result("ACTION_NOT_ALLOWED", f"policy_denied: '{cmd_prefix or '?'}' not in allowed_exec for '{blueprint_id}'")
    return None


def _build_timed_exec_command(command, timeout):
    import shlex

    timeout_s = max(1, int(timeout or 30))
    cmd_escaped = shlex.quote(str(command or ""))
    marker = EXEC_TIMEOUT_MARKER
    script = (
        f"cmd={cmd_escaped}; "
        "flag=/tmp/.trion_exec_timeout_$$; "
        'sh -lc "$cmd" & cmd_pid=$!; '
        '(SP=; trap \'kill "$SP" 2>/dev/null; exit\' TERM; '
        f'sleep {timeout_s} & SP=$!; wait "$SP"; '
        'echo 1 > "$flag"; kill -TERM "$cmd_pid" 2>/dev/null; '
        'SP=; sleep 1 & SP=$!; wait "$SP"; '
        'kill -KILL "$cmd_pid" 2>/dev/null) & killer_pid=$!; '
        'wait "$cmd_pid"; rc=$?; '
        'if [ -f "$flag" ]; then rm -f "$flag"; '
        'kill "$killer_pid" 2>/dev/null || true; wait "$killer_pid" 2>/dev/null || true; '
        f'echo "{marker}" >&2; exit {EXEC_TIMEOUT_EXIT_CODE}; fi; '
        'kill "$killer_pid" 2>/dev/null || true; wait "$killer_pid" 2>/dev/null || true; '
        'exit "$rc"'
    )
    return f"sh -lc {shlex.quote(script)}"


def _extract_timeout_marker(stderr):
    text = str(stderr or "")
    if EXEC_TIMEOUT_MARKER not in text:
        return text, False
    return text.replace(EXEC_TIMEOUT_MARKER, "").strip(), True


def _exec_run_with_workdir_fallback(container, timed_command):
    result = container.exec_run(timed_command, demux=True, workdir="/workspace")
    try:
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace") if isinstance(result.output, tuple) else ""
    except Exception:
        stderr = ""
    if int(getattr(result, "exit_code", 0) or 0) != 127 or "chdir to cwd" not in stderr.lower():
        return result
    return container.exec_run(timed_command, demux=True, workdir="/")


def container_exec(container_ref, command, timeout=30):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_ref)
        if str(getattr(container, "status", "") or "").strip().lower() != "running":
            return {"exit_code": -1, "output": f"Container is not running (status: {container.status})", "container_id": container_ref}
        blocked = _check_exec_policy(container, command)
        if blocked:
            return blocked
        timed_cmd = _build_timed_exec_command(command, timeout)
        result = _exec_run_with_workdir_fallback(container, timed_cmd)
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace") if result.output[1] else ""
        stderr, timed_out = _extract_timeout_marker(stderr)
        exit_code = int(getattr(result, "exit_code", 0) or 0)
        if timed_out:
            exit_code = EXEC_TIMEOUT_EXIT_CODE
            stderr = f"{stderr}\nCommand timed out after {max(1, int(timeout or 30))}s" if stderr else f"Command timed out after {max(1, int(timeout or 30))}s"
        output = (stdout + ("\n" + stderr if stderr else "")).strip()
        return {"exit_code": exit_code, "output": output, "container_id": str(getattr(container, "id", "") or container_ref), "timed_out": timed_out}
    except Exception as exc:
        if is_not_found(exc):
            return {"exit_code": -1, "output": "Container not found", "container_id": container_ref}
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def container_exec_detailed(container_ref, command, timeout=30):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_ref)
        if str(getattr(container, "status", "") or "").strip().lower() != "running":
            return {"exit_code": -1, "stdout": "", "stderr": f"Container is not running (status: {container.status})", "truncated": False, "container_id": container_ref}
        blocked = _check_exec_policy(container, command)
        if blocked:
            return blocked
        timed_cmd = _build_timed_exec_command(command, timeout)
        result = _exec_run_with_workdir_fallback(container, timed_cmd)
        stdout = (result.output[0] or b"").decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = (result.output[1] or b"").decode("utf-8", errors="replace") if result.output[1] else ""
        stderr, timed_out = _extract_timeout_marker(stderr)
        exit_code = int(getattr(result, "exit_code", 0) or 0)
        if timed_out:
            exit_code = EXEC_TIMEOUT_EXIT_CODE
            stderr = f"{stderr}\nCommand timed out after {max(1, int(timeout or 30))}s" if stderr else f"Command timed out after {max(1, int(timeout or 30))}s"
        truncated = len(stdout) > MAX_EXEC_OUTPUT or len(stderr) > MAX_EXEC_OUTPUT
        return {
            "exit_code": exit_code,
            "stdout": stdout[:MAX_EXEC_OUTPUT].strip(),
            "stderr": stderr[:MAX_EXEC_OUTPUT].strip(),
            "truncated": truncated,
            "timed_out": timed_out,
            "container_id": str(getattr(container, "id", "") or container_ref),
        }
    except Exception as exc:
        if is_not_found(exc):
            return {"exit_code": -1, "stdout": "", "stderr": "Container not found", "truncated": False, "container_id": container_ref}
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def runtime_cleanup_all():
    try:
        client = get_docker_client()
        removed = []
        errors = []
        for container in client.containers.list(all=True):
            summary = container_summary(container)
            if not bool(summary.get("managed_by_trion")):
                continue
            container_id = str(getattr(container, "id", "") or "")
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            try:
                container.remove(force=True)
                removed.append(container_id)
            except Exception as exc:
                errors.append({"container_id": container_id, "error": str(exc)})
        return {"cleaned": True, "removed": removed, "errors": errors}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def remove_stopped_container(container_ref):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_ref)
        labels = dict(container.labels or {})
        summary = container_summary(container)
        if not bool(summary.get("managed_by_trion")):
            return {"removed": False, "container_id": container_ref, "reason": "not_managed"}
        container.reload()
        if bool(((container.attrs or {}).get("State") or {}).get("Running")):
            return {"removed": False, "container_id": container_ref, "reason": "running"}
        blueprint_id = str(labels.get("trion.blueprint") or "unknown")
        container.remove(force=True)
        return {"removed": True, "container_id": str(getattr(container, "id", "") or container_ref), "blueprint_id": blueprint_id}
    except Exception as exc:
        if is_not_found(exc):
            return {"removed": False, "container_id": container_ref, "reason": "not_found"}
        return {"removed": False, "container_id": container_ref, "reason": "error", "error": str(exc)}


def list_networks():
    try:
        client = get_docker_client()
        result = []
        for net in client.networks.list(filters={"label": TRION_LABEL}):
            labels = dict((net.attrs or {}).get("Labels") or {})
            containers = dict((net.attrs or {}).get("Containers") or {})
            result.append(
                {
                    "name": net.name,
                    "id": getattr(net, "short_id", "") or "",
                    "type": str(labels.get("trion.network.type") or "unknown"),
                    "internal": bool((net.attrs or {}).get("Internal", False)),
                    "driver": str((net.attrs or {}).get("Driver") or ""),
                    "container_count": len(containers),
                    "containers": [str((item or {}).get("Name") or "") for item in containers.values()] if containers else [],
                }
            )
        return {"networks": result}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_network_info(container_id):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_id)
        networks = dict(((container.attrs or {}).get("NetworkSettings") or {}).get("Networks") or {})
        return {
            "container_id": container_id,
            "networks": {
                name: {
                    "ip": str((config or {}).get("IPAddress") or ""),
                    "gateway": str((config or {}).get("Gateway") or ""),
                    "mac": str((config or {}).get("MacAddress") or ""),
                }
                for name, config in networks.items()
            },
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def _remove_network(network_name):
    try:
        client = get_docker_client()
        net = client.networks.get(network_name)
        labels = dict((net.attrs or {}).get("Labels") or {})
        if str(labels.get("trion.managed") or "").strip().lower() != "true":
            return False
        net.remove()
        return True
    except Exception as exc:
        if is_not_found(exc):
            return False
        if "has active endpoints" in str(exc).lower():
            return False
        raise


def cleanup_networks():
    try:
        removed = []
        for network in list_networks().get("networks", []):
            if str(network.get("type") or "") != "isolated":
                continue
            if int(network.get("container_count") or 0) != 0:
                continue
            name = str(network.get("name") or "").strip()
            if name and _remove_network(name):
                removed.append(name)
        return {"removed": removed}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def list_volumes(blueprint_id=""):
    try:
        client = get_docker_client()
        result = []
        for volume in client.volumes.list(filters={"label": TRION_LABEL}):
            labels = dict((volume.attrs or {}).get("Labels") or {})
            bp = str(labels.get("trion.blueprint") or "")
            if blueprint_id and bp != blueprint_id:
                continue
            result.append(
                {
                    "name": volume.name,
                    "blueprint_id": bp,
                    "created_at": str(labels.get("trion.created") or (volume.attrs or {}).get("CreatedAt") or ""),
                    "driver": str((volume.attrs or {}).get("Driver") or "local"),
                    "mountpoint": str((volume.attrs or {}).get("Mountpoint") or ""),
                }
            )
        result.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {"volumes": result}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def list_snapshots(volume_name=""):
    if not os.path.exists(SNAPSHOT_DIR):
        return {"snapshots": []}
    result = []
    for filename in sorted(os.listdir(SNAPSHOT_DIR), reverse=True):
        if not filename.endswith(".tar.gz"):
            continue
        if volume_name and not filename.startswith(volume_name):
            continue
        filepath = os.path.join(SNAPSHOT_DIR, filename)
        stat = os.stat(filepath)
        result.append(
            {
                "filename": filename,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    return {"snapshots": result}


def delete_snapshot(filename):
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return {"deleted": True, "filename": filename}
        return {"deleted": False, "filename": filename}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def create_snapshot(volume_name, tag=""):
    try:
        client = get_docker_client()
        try:
            client.volumes.get(volume_name)
        except Exception as exc:
            if is_not_found(exc):
                return {"created": False, "filename": "", "volume": volume_name}
            return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        tag_part = f"_{tag}" if tag else ""
        filename = f"{volume_name}{tag_part}_{ts}.tar.gz"
        filepath = os.path.join(SNAPSHOT_DIR, filename)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)

        container = None
        try:
            container = client.containers.run(
                "alpine:latest",
                command="sh -c 'mkdir -p /backup && tar czf /backup/snapshot.tar.gz -C /workspace .'",
                volumes={volume_name: {"bind": "/workspace", "mode": "ro"}},
                detach=True,
                remove=False,
                labels={"trion.managed": "true", "trion.temp": "snapshot"},
            )
            result = container.wait(timeout=120)
            exit_code = result.get("StatusCode", -1) if isinstance(result, dict) else -1
            if int(exit_code) != 0:
                return {"created": False, "filename": "", "volume": volume_name}

            bits, _stat = container.get_archive("/backup/snapshot.tar.gz")
            raw = b"".join(bits)
            outer_tar = tarfile.open(fileobj=io.BytesIO(raw), mode="r")
            members = outer_tar.getmembers()
            if not members:
                return {"created": False, "filename": "", "volume": volume_name}
            inner_file = outer_tar.extractfile(members[0])
            if inner_file is None:
                return {"created": False, "filename": "", "volume": volume_name}
            with open(filepath, "wb") as handle:
                handle.write(inner_file.read())
            return {"created": True, "filename": filename, "volume": volume_name}
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def restore_snapshot(snapshot_filename, target_volume=""):
    try:
        client = get_docker_client()
        filepath = os.path.join(SNAPSHOT_DIR, snapshot_filename)
        if not os.path.exists(filepath):
            return {"restored": False, "volume": "", "filename": snapshot_filename}

        volume_name = str(target_volume or "").strip()
        if not volume_name:
            base = snapshot_filename.rsplit("_", 2)[0] if "_" in snapshot_filename else "restored"
            ts = str(int(datetime.now(timezone.utc).timestamp()))
            volume_name = f"{base}_restored_{ts}"

        try:
            client.volumes.get(volume_name)
        except Exception as exc:
            if is_not_found(exc):
                client.volumes.create(
                    name=volume_name,
                    driver="local",
                    labels={
                        "trion.managed": "true",
                        "trion.restored_from": snapshot_filename,
                        "trion.created": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)

        container = None
        try:
            container = client.containers.create(
                "alpine:latest",
                command="tar xzf /backup/snapshot.tar.gz -C /workspace",
                volumes={volume_name: {"bind": "/workspace", "mode": "rw"}},
                labels={"trion.managed": "true", "trion.temp": "restore"},
            )
            with open(filepath, "rb") as handle:
                tar_data = handle.read()

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                info = tarfile.TarInfo(name="snapshot.tar.gz")
                info.size = len(tar_data)
                tar.addfile(info, io.BytesIO(tar_data))
            tar_stream.seek(0)

            container.put_archive("/backup", tar_stream.read())
            container.start()
            result = container.wait(timeout=120)
            exit_code = result.get("StatusCode", -1) if isinstance(result, dict) else -1
            if int(exit_code) != 0:
                return {"restored": False, "volume": "", "filename": snapshot_filename}
            return {"restored": True, "volume": volume_name, "filename": snapshot_filename}
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_volume(volume_name):
    try:
        client = get_docker_client()
        volume = client.volumes.get(volume_name)
        labels = dict((volume.attrs or {}).get("Labels") or {})
        return {
            "volume": {
                "name": volume.name,
                "blueprint_id": str(labels.get("trion.blueprint") or ""),
                "created_at": str(labels.get("trion.created") or (volume.attrs or {}).get("CreatedAt") or ""),
                "driver": str((volume.attrs or {}).get("Driver") or "local"),
                "mountpoint": str((volume.attrs or {}).get("Mountpoint") or ""),
                "snapshots": list_snapshots(volume_name).get("snapshots", []),
            }
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("VOLUME_NOT_FOUND", f"Volume '{volume_name}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def remove_volume(volume_name, force=False):
    try:
        client = get_docker_client()
        volume = client.volumes.get(volume_name)
        volume.remove(force=bool(force))
        return {"removed": True, "volume": volume_name}
    except Exception as exc:
        if is_not_found(exc):
            return {"removed": False, "volume": volume_name}
        if "volume is in use" in str(exc).lower():
            return {"removed": False, "volume": volume_name}
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def cleanup_orphaned_volumes(dry_run=True):
    try:
        client = get_docker_client()
        active_volumes = set()
        for container in client.containers.list(all=True):
            for mount in (container.attrs or {}).get("Mounts", []):
                name = str((mount or {}).get("Name") or "").strip()
                if name:
                    active_volumes.add(name)

        orphaned = []
        for volume in client.volumes.list(filters={"label": TRION_LABEL}):
            if volume.name in active_volumes:
                continue
            orphaned.append(volume.name)
            if not dry_run:
                volume.remove()
        return {"orphaned": orphaned, "dry_run": bool(dry_run)}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def start_stopped_container(container_id):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_id)
        blocked = guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() == "running":
            return action_result(container, "already_running")
        container.start()
        container.reload()
        return action_result(container, "started")
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def stop_container(container_id):
    try:
        client = get_docker_client()
        container = resolve_container_reference(client, container_id)
        blocked = guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() != "running":
            return action_result(container, "already_stopped")
        container.stop(timeout=10)
        container.reload()
        return action_result(container, "stopped")
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


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


def json_text(value, default):
    return json.dumps(value if value is not None else default)


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


def parse_simple_yaml(yaml_content):
    data = {}
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
            parsed = None
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


def yaml_load(yaml_content):
    if yaml is not None:
        data = yaml.safe_load(yaml_content) or {}
    else:
        data = parse_simple_yaml(yaml_content)
    if not isinstance(data, dict):
        raise ValueError("yaml must describe an object")
    return data


def yaml_dump(data):
    if yaml is not None:
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    lines = []
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
    detail = get_blueprint(params["id"]).get("blueprint", {})
    return {"created": True, "blueprint": detail, "trust": blueprint_trust(detail)}


def update_blueprint(blueprint_id, updates):
    existing = get_blueprint(blueprint_id).get("blueprint")
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
    detail = get_blueprint(blueprint_id).get("blueprint", {})
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
    detail = get_blueprint(blueprint_id).get("blueprint")
    if not isinstance(detail, dict):
        return error_result("BLUEPRINT_NOT_FOUND", f"Blueprint '{blueprint_id}' not found")
    return {"blueprint_id": blueprint_id, "yaml": yaml_dump(detail.get("definition") or {})}


def handle_request(payload):
    method = payload.get("method", "")
    request_id = payload.get("id")
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "container-commander", "version": "2.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = ((params.get("name") or "").strip())
        arguments = (params.get("arguments") or {})
        if name == "container_list":
            result = list_containers()
        elif name == "container_inspect":
            result = inspect_container(str(arguments.get("container_id") or arguments.get("container_name") or ""))
        elif name == "container_logs":
            result = get_container_logs(
                str(arguments.get("container_id") or arguments.get("container_name") or ""),
                tail=arguments.get("tail", 200),
                since=str(arguments.get("since") or ""),
                limit_chars=arguments.get("limit_chars", 16000),
            )
        elif name == "container_stats":
            result = get_container_stats(str(arguments.get("container_id") or arguments.get("container_name") or ""))
        elif name == "runtime_quota":
            result = runtime_quota()
        elif name == "container_exec":
            result = container_exec(
                str(arguments.get("container_id") or arguments.get("container_name") or ""),
                str(arguments.get("command") or ""),
                timeout=arguments.get("timeout", 30),
            )
        elif name == "container_exec_detailed":
            result = container_exec_detailed(
                str(arguments.get("container_id") or arguments.get("container_name") or ""),
                str(arguments.get("command") or ""),
                timeout=arguments.get("timeout", 30),
            )
        elif name == "runtime_cleanup_all":
            result = runtime_cleanup_all()
        elif name == "remove_stopped_container":
            result = remove_stopped_container(str(arguments.get("container_id") or arguments.get("container_name") or ""))
        elif name == "network_list":
            result = list_networks()
        elif name == "network_info":
            result = get_network_info(str(arguments.get("container_id") or arguments.get("container_name") or ""))
        elif name == "network_cleanup":
            result = cleanup_networks()
        elif name == "proxy_start":
            result = ensure_proxy_running()
        elif name == "proxy_stop":
            result = stop_proxy()
        elif name == "proxy_whitelist_get":
            result = get_whitelist(str(arguments.get("blueprint_id") or ""))
        elif name == "proxy_whitelist_set":
            result = set_whitelist(str(arguments.get("blueprint_id") or ""), arguments.get("domains") or [])
        elif name == "dashboard_overview":
            result = get_dashboard_overview()
        elif name == "host_companion_check":
            result = check_host_companion(str(arguments.get("blueprint_id") or ""))
        elif name == "host_companion_repair":
            result = repair_host_companion(str(arguments.get("blueprint_id") or ""))
        elif name == "host_companion_uninstall":
            result = uninstall_host_companion(str(arguments.get("blueprint_id") or ""))
        elif name == "package_manifest_get":
            result = get_package_manifest(str(arguments.get("blueprint_id") or ""))
        elif name == "marketplace_bundle_list":
            bundles = list_bundles()
            result = {"bundles": bundles, "count": len(bundles)}
        elif name == "marketplace_starter_list":
            starters = get_starters()
            result = {"starters": starters, "count": len(starters)}
        elif name == "marketplace_catalog_list":
            result = list_catalog(
                category=str(arguments.get("category") or ""),
                trusted_only=bool(arguments.get("trusted_only", False)),
            )
        elif name == "marketplace_catalog_sync":
            result = sync_remote_catalog(
                repo_url=str(arguments.get("repo_url") or ""),
                branch=str(arguments.get("branch") or "main"),
            )
        elif name == "marketplace_starter_install":
            result = install_starter(str(arguments.get("starter_id") or ""))
        elif name == "marketplace_catalog_install":
            result = install_catalog_blueprint(
                str(arguments.get("blueprint_id") or ""),
                overwrite=bool(arguments.get("overwrite", False)),
            )
        elif name == "marketplace_bundle_export":
            filename = export_bundle(str(arguments.get("blueprint_id") or ""))
            result = {"exported": bool(filename), "filename": filename or "", "blueprint_id": str(arguments.get("blueprint_id") or "")}
        elif name == "marketplace_bundle_import":
            import base64

            bundle_bytes = base64.b64decode(str(arguments.get("bundle_bytes_b64") or "").encode("utf-8"))
            result = import_bundle(
                bundle_bytes,
                filename=str(arguments.get("filename") or ""),
                overwrite=bool(arguments.get("overwrite", False)),
            ) or {"error": "import_failed"}
        elif name == "volume_list":
            result = list_volumes(str(arguments.get("blueprint_id") or ""))
        elif name == "volume_get":
            result = get_volume(str(arguments.get("volume_name") or ""))
        elif name == "volume_remove":
            result = remove_volume(str(arguments.get("volume_name") or ""), force=bool(arguments.get("force")))
        elif name == "volume_cleanup":
            result = cleanup_orphaned_volumes(dry_run=bool(arguments.get("dry_run", True)))
        elif name == "snapshot_list":
            result = list_snapshots(str(arguments.get("volume_name") or ""))
        elif name == "snapshot_delete":
            result = delete_snapshot(str(arguments.get("filename") or ""))
        elif name == "snapshot_create":
            result = create_snapshot(
                str(arguments.get("volume_name") or ""),
                tag=str(arguments.get("tag") or ""),
            )
        elif name == "snapshot_restore":
            result = restore_snapshot(
                str(arguments.get("filename") or ""),
                target_volume=str(arguments.get("target_volume") or ""),
            )
        elif name == "blueprint_list":
            result = list_blueprints()
        elif name == "blueprint_get":
            result = get_blueprint(str(arguments.get("blueprint_id") or ""))
        elif name == "blueprint_create":
            result = create_blueprint(arguments.get("blueprint") or {})
        elif name == "blueprint_update":
            result = update_blueprint(str(arguments.get("blueprint_id") or ""), arguments.get("updates") or {})
        elif name == "blueprint_delete":
            result = delete_blueprint(str(arguments.get("blueprint_id") or ""))
        elif name == "blueprint_import_yaml":
            result = import_blueprint_yaml(str(arguments.get("yaml") or ""))
        elif name == "blueprint_export_yaml":
            result = export_blueprint_yaml(str(arguments.get("blueprint_id") or ""))
        elif name == "start_stopped_container":
            result = start_stopped_container(str(arguments.get("container_id") or arguments.get("container_name") or ""))
        elif name == "stop_container":
            result = stop_container(str(arguments.get("container_id") or arguments.get("container_name") or ""))
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("method") == "notifications/initialized":
            continue
        print(json.dumps(handle_request(payload)), flush=True)


if __name__ == "__main__":
    main()
