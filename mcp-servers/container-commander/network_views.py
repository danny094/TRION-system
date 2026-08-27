from __future__ import annotations

from typing import Any

from contracts import error_result
from container_reference import ContainerReferenceError, resolve_container_reference


def _client():
    from docker import from_env

    return from_env()


def _is_not_found(error: Exception) -> bool:
    return error.__class__.__name__ == "NotFound"


def list_networks() -> dict[str, Any]:
    try:
        result: list[dict[str, Any]] = []
        for net in _client().networks.list(filters={"label": "trion.managed"}):
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


def get_network_info(container_id: str = "", container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        networks = dict(((container.attrs or {}).get("NetworkSettings") or {}).get("Networks") or {})
        return {
            "container_id": str(getattr(container, "id", "") or container_id or container_name),
            "networks": {
                name: {
                    "ip": str((config or {}).get("IPAddress") or ""),
                    "gateway": str((config or {}).get("Gateway") or ""),
                    "mac": str((config or {}).get("MacAddress") or ""),
                }
                for name, config in networks.items()
            },
        }
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            container_ref = container_id or container_name
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def _remove_network(network_name: str) -> bool:
    try:
        net = _client().networks.get(network_name)
        labels = dict((net.attrs or {}).get("Labels") or {})
        if str(labels.get("trion.managed") or "").strip().lower() != "true":
            return False
        net.remove()
        return True
    except Exception as exc:
        if _is_not_found(exc):
            return False
        if "has active endpoints" in str(exc).lower():
            return False
        raise


def cleanup_networks() -> dict[str, Any]:
    try:
        removed: list[str] = []
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
