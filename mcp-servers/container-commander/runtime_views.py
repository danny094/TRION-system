from __future__ import annotations

from typing import Any

from contracts import ContainerInspect, ContainerLogsResult, error_result
from home_runtime import commander_home_scope, home_blueprint_id
from runtime_shared import _action_result, _guard_managed_action, _is_not_found, _managed_flags, _port_rows, _quota_limits, _summary
from runtime_stats import stats_payload
from container_reference import ContainerReferenceError, resolve_container_reference


def _client():
    from docker import from_env

    return from_env()


def get_runtime_quota() -> dict[str, Any]:
    try:
        max_mem_mb, max_cpu, max_containers = _quota_limits()
        containers = _client().containers.list(all=True)
        managed = [container for container in containers if _summary(container).managed_by_trion]

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


def list_containers() -> dict[str, Any]:
    try:
        containers = _client().containers.list(all=True)
        return {"containers": [_summary(container).model_dump() for container in containers]}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def inspect_container(container_id: str = "", container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        summary = _summary(container)
        labels = dict(container.labels or {})
        inspect = ContainerInspect(
            **summary.model_dump(),
            blueprint_id=home_blueprint_id(labels),
            labels=labels,
            ports=_port_rows(container),
            mounts=[
                f"{mount.get('Source', '?')}:{mount.get('Destination', '?')}"
                for mount in (container.attrs or {}).get("Mounts", [])
            ],
            runtime_state=dict((container.attrs or {}).get("State") or {}),
            home_scope=commander_home_scope(container, labels),
        )
        return {"container": inspect.model_dump()}
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            container_ref = container_id or container_name
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_logs(container_id: str = "", tail: int = 200, since: str = "", limit_chars: int = 16000, container_name: str = "") -> dict[str, Any]:
    safe_tail = max(1, min(int(tail), 500))
    safe_limit = max(256, min(int(limit_chars), 64000))
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        raw = container.logs(tail=safe_tail, timestamps=True, since=since or None)
        logs = raw.decode("utf-8", errors="replace")
        truncated = len(logs) > safe_limit
        if truncated:
            logs = logs[-safe_limit:]
        resolved_container_id = str(getattr(container, "id", "") or container_id or container_name)
        result = ContainerLogsResult(
            container_id=resolved_container_id,
            logs=logs,
            truncated=truncated,
            tail=safe_tail,
            since=str(since or ""),
            limit_chars=safe_limit,
        )
        return result.model_dump()
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            container_ref = container_id or container_name
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_stats(container_id: str = "", container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        resolved_container_id = str(getattr(container, "id", "") or container_id or container_name)
        return stats_payload(resolved_container_id, dict(container.attrs or {}), container.stats(stream=False), _port_rows(container))
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            container_ref = container_id or container_name
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)
