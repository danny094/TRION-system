from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from contracts import ContainerInspect, ContainerLogsResult, ContainerSummary, error_result
from home_runtime import commander_home_scope, home_blueprint_id


def _client():
    from docker import from_env

    return from_env()


def _is_not_found(error: Exception) -> bool:
    return error.__class__.__name__ == "NotFound"


def _is_true(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _managed_flags(labels: dict[str, str]) -> tuple[bool, bool, bool]:
    managed = _is_true(labels.get("trion.managed")) or "trion.blueprint" in labels
    protected = _is_true(labels.get("trion.protected")) or _is_true(labels.get("trion.system"))
    actions_allowed = managed and not protected
    return managed, actions_allowed, protected


def _created_at(container: Any) -> str:
    created = getattr(container, "attrs", {}).get("Created", "")
    if created:
        return str(created)
    return datetime.now(timezone.utc).isoformat()


def _port_rows(container: Any) -> list[dict[str, str]]:
    ports = ((container.attrs or {}).get("NetworkSettings") or {}).get("Ports") or {}
    rows: list[dict[str, str]] = []
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


def _summary(container: Any) -> ContainerSummary:
    labels = dict(container.labels or {})
    managed, actions_allowed, protected = _managed_flags(labels)
    image = getattr(getattr(container, "image", None), "tags", None) or []
    return ContainerSummary(
        container_id=container.id,
        name=container.name,
        image=image[0] if image else str((container.attrs or {}).get("Config", {}).get("Image") or ""),
        status=str(container.status or "unknown"),
        created_at=_created_at(container),
        managed_by_trion=managed,
        actions_allowed=actions_allowed,
        protected=protected,
    )


def _quota_limits() -> tuple[int, float, int]:
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
    return max_mem_mb, max_cpu, max_containers


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


def _action_result(container: Any, action: str) -> dict[str, Any]:
    return {
        "ok": True,
        "action": action,
        "container": _summary(container).model_dump(),
    }


def _guard_managed_action(container: Any) -> dict[str, Any] | None:
    summary = _summary(container)
    if not summary.managed_by_trion:
        return error_result("ACTION_NOT_ALLOWED", f"Container '{summary.name}' is not managed by TRION")
    if summary.protected:
        return error_result("ACTION_NOT_ALLOWED", f"Container '{summary.name}' is protected")
    if not summary.actions_allowed:
        return error_result("ACTION_NOT_ALLOWED", f"Actions are not allowed for container '{summary.name}'")
    return None


def list_containers() -> dict[str, Any]:
    try:
        containers = _client().containers.list(all=True)
        return {"containers": [_summary(container).model_dump() for container in containers]}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def inspect_container(container_id: str) -> dict[str, Any]:
    try:
        container = _client().containers.get(container_id)
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
    except Exception as exc:
        if _is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_logs(container_id: str, tail: int = 200, since: str = "", limit_chars: int = 16000) -> dict[str, Any]:
    safe_tail = max(1, min(int(tail), 500))
    safe_limit = max(256, min(int(limit_chars), 64000))
    try:
        container = _client().containers.get(container_id)
        raw = container.logs(tail=safe_tail, timestamps=True, since=since or None)
        logs = raw.decode("utf-8", errors="replace")
        truncated = len(logs) > safe_limit
        if truncated:
            logs = logs[-safe_limit:]
        result = ContainerLogsResult(
            container_id=container_id,
            logs=logs,
            truncated=truncated,
            tail=safe_tail,
            since=str(since or ""),
            limit_chars=safe_limit,
        )
        return result.model_dump()
    except Exception as exc:
        if _is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_stats(container_id: str) -> dict[str, Any]:
    try:
        container = _client().containers.get(container_id)
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
            "ports": _port_rows(container),
            "efficiency": {"score": round(score, 2), "level": level},
            "deploy_warnings": [],
        }
    except Exception as exc:
        if _is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def start_stopped_container(container_id: str) -> dict[str, Any]:
    try:
        container = _client().containers.get(container_id)
        blocked = _guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() == "running":
            return _action_result(container, "already_running")
        container.start()
        container.reload()
        return _action_result(container, "started")
    except Exception as exc:
        if _is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def stop_container(container_id: str) -> dict[str, Any]:
    try:
        container = _client().containers.get(container_id)
        blocked = _guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() != "running":
            return _action_result(container, "already_stopped")
        container.stop(timeout=10)
        container.reload()
        return _action_result(container, "stopped")
    except Exception as exc:
        if _is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_id}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def remove_stopped_container(container_id: str) -> dict[str, Any]:
    try:
        container = _client().containers.get(container_id)
        labels = dict(container.labels or {})
        summary = _summary(container)
        if not summary.managed_by_trion:
            return {"removed": False, "container_id": container_id, "reason": "not_managed"}
        container.reload()
        if bool(((container.attrs or {}).get("State") or {}).get("Running")):
            return {"removed": False, "container_id": container_id, "reason": "running"}
        blueprint_id = str(labels.get("trion.blueprint") or "unknown")
        container.remove(force=True)
        return {"removed": True, "container_id": container_id, "blueprint_id": blueprint_id}
    except Exception as exc:
        if _is_not_found(exc):
            return {"removed": False, "container_id": container_id, "reason": "not_found"}
        return {"removed": False, "container_id": container_id, "reason": "error", "error": str(exc)}


def cleanup_all() -> dict[str, Any]:
    try:
        client = _client()
        removed: list[str] = []
        errors: list[dict[str, str]] = []
        for container in client.containers.list(all=True):
            labels = dict(container.labels or {})
            managed, _, _ = _managed_flags(labels)
            if not managed:
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
