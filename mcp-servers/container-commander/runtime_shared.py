from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from contracts import ContainerSummary, error_result


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
    attrs = dict(container.attrs or {})
    image = str((attrs.get("Config") or {}).get("Image") or attrs.get("Image") or "")
    return ContainerSummary(
        container_id=container.id,
        name=container.name,
        image=image,
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
