#!/usr/bin/env python3
from datetime import datetime, timezone

from bundle_blueprint_store import list_blueprints
from bundle_network import list_networks
from bundle_runtime_views import list_containers
from bundle_volumes import list_volumes
from proxy_views import get_whitelist


def _now():
    return datetime.now(timezone.utc).isoformat()


def _runtime_error(result):
    if isinstance(result, dict) and result.get("ok") is False and isinstance(result.get("error"), dict):
        return str((result.get("error") or {}).get("message") or "runtime_unavailable")
    return ""


def get_dashboard_overview():
    containers_result = list_containers()
    blueprints_result = list_blueprints()
    networks_result = list_networks()
    volumes_result = list_volumes()

    containers = containers_result.get("containers") if isinstance(containers_result.get("containers"), list) else []
    blueprints = blueprints_result.get("blueprints") if isinstance(blueprints_result.get("blueprints"), list) else []
    networks = networks_result.get("networks") if isinstance(networks_result.get("networks"), list) else []
    volumes = volumes_result.get("volumes") if isinstance(volumes_result.get("volumes"), list) else []

    runtime_errors = [
        message
        for message in (
            _runtime_error(containers_result),
            _runtime_error(networks_result),
            _runtime_error(volumes_result),
        )
        if message
    ]
    alert_messages = [f"runtime_unavailable:{message}" for message in runtime_errors]
    if isinstance(blueprints_result, dict) and blueprints_result.get("ok") is False:
        alert_messages.append(
            "blueprint_store_unavailable:" + str((blueprints_result.get("error") or {}).get("message") or "unknown")
        )

    proxy_state = get_whitelist("_dashboard_proxy_state")
    proxy_enabled = bool(proxy_state.get("enabled")) if isinstance(proxy_state, dict) else False

    return {
        "generated_at": _now(),
        "health": {
            "runtime": "degraded" if runtime_errors else "ok",
            "blueprint_store": "ok" if blueprints_result.get("ok") is not False else "degraded",
            "proxy_policy": "enabled" if proxy_enabled else "disabled",
        },
        "resources": {
            "containers": {
                "total": len(containers),
                "running": sum(1 for item in containers if str(item.get("status") or "").strip() == "running"),
                "stopped": sum(1 for item in containers if str(item.get("status") or "").strip() in {"exited", "stopped"}),
            },
            "blueprints": {"total": len(blueprints)},
            "networks": {"total": len(networks)},
            "volumes": {"total": len(volumes)},
        },
        "alerts": [{"level": "warn", "message": message} for message in alert_messages],
        "events": [],
    }
