from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Tuple

from commander_api.mcp_runtime import stop_container_via_mcp
from commander_deploy_runtime_client import TRION_LABEL, emit_ws_activity, get_runtime_client
from models import ContainerInstance, ContainerStatus, ResourceLimits, SessionQuota


logger = logging.getLogger(__name__)


@dataclass
class RuntimeStateRefs:
    active: Dict[str, ContainerInstance]
    ttl_timers: Dict[str, threading.Timer]
    quota: SessionQuota
    state_lock: Any
    pending_starts: int
    pending_memory_mb: float
    pending_cpu: float
    last_runtime_sync_monotonic: float


_active: Dict[str, ContainerInstance] = {}
_ttl_timers: Dict[str, threading.Timer] = {}
_state_lock = threading.RLock()
_pending_starts = 0
_pending_memory_mb = 0.0
_pending_cpu = 0.0
_last_runtime_sync_monotonic = 0.0
_quota: SessionQuota | None = None


def parse_memory(mem_str: str) -> int:
    s = str(mem_str or "").strip().lower()
    if s.endswith("g"):
        return int(float(s[:-1]) * 1024 * 1024 * 1024)
    if s.endswith("m"):
        return int(float(s[:-1]) * 1024 * 1024)
    if s.endswith("k"):
        return int(float(s[:-1]) * 1024)
    return int(s)


def build_quota_from_env() -> SessionQuota:
    env_mem = os.environ.get("COMMANDER_MAX_MEMORY_MB", "").strip()
    env_cpu = os.environ.get("COMMANDER_MAX_CPU", "").strip()
    env_containers = os.environ.get("COMMANDER_MAX_CONTAINERS", "").strip()

    if env_mem:
        max_mem_mb = max(512, int(env_mem))
    else:
        try:
            with open("/proc/meminfo", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        max_mem_mb = max(2048, int(line.split()[1]) // 1024 - 4096)
                        break
                else:
                    max_mem_mb = 2048
        except Exception:
            max_mem_mb = 2048

    max_cpu = max(0.5, float(env_cpu)) if env_cpu else max(2.0, float(os.cpu_count() or 2) - 2.0)
    max_containers = int(env_containers) if env_containers else 5
    quota = SessionQuota(max_total_memory_mb=max_mem_mb, max_total_cpu=max_cpu, max_containers=max_containers)
    logger.info("[CommanderDeployState] Quota: memory=%s MB, cpu=%s, containers=%s", max_mem_mb, max_cpu, max_containers)
    return quota


def _get_quota() -> SessionQuota:
    global _quota
    if _quota is None:
        _quota = build_quota_from_env()
    return _quota


def build_refs() -> RuntimeStateRefs:
    return RuntimeStateRefs(
        active=_active,
        ttl_timers=_ttl_timers,
        quota=_get_quota(),
        state_lock=_state_lock,
        pending_starts=_pending_starts,
        pending_memory_mb=_pending_memory_mb,
        pending_cpu=_pending_cpu,
        last_runtime_sync_monotonic=_last_runtime_sync_monotonic,
    )


def apply_refs(state: RuntimeStateRefs) -> None:
    global _pending_starts, _pending_memory_mb, _pending_cpu, _last_runtime_sync_monotonic
    _pending_starts = state.pending_starts
    _pending_memory_mb = state.pending_memory_mb
    _pending_cpu = state.pending_cpu
    _last_runtime_sync_monotonic = state.last_runtime_sync_monotonic


def update_quota_used_unlocked(state: RuntimeStateRefs) -> None:
    state.quota.containers_used = len(state.active)
    state.quota.memory_used_mb = sum(item.memory_limit_mb for item in state.active.values())
    state.quota.cpu_used = sum(item.cpu_limit_alloc for item in state.active.values())


def reserve_quota(resources: ResourceLimits, state: RuntimeStateRefs) -> Tuple[float, float]:
    mem_mb = parse_memory(resources.memory_limit) / (1024 * 1024)
    cpu = float(resources.cpu_limit)
    with state.state_lock:
        containers_total = len(state.active) + state.pending_starts
        if containers_total >= state.quota.max_containers:
            raise RuntimeError(
                f"Container quota exceeded: {containers_total}/{state.quota.max_containers} running_or_pending"
            )
        mem_total = state.quota.memory_used_mb + state.pending_memory_mb + mem_mb
        if mem_total > state.quota.max_total_memory_mb:
            raise RuntimeError(f"Memory quota exceeded: {int(mem_total)} > {state.quota.max_total_memory_mb} MB")
        cpu_total = state.quota.cpu_used + state.pending_cpu + cpu
        if cpu_total > state.quota.max_total_cpu:
            raise RuntimeError(f"CPU quota exceeded: {cpu_total} > {state.quota.max_total_cpu}")
        state.pending_starts += 1
        state.pending_memory_mb += mem_mb
        state.pending_cpu += cpu
    return mem_mb, cpu


def release_quota_reservation(mem_mb: float, cpu: float, state: RuntimeStateRefs) -> None:
    with state.state_lock:
        state.pending_starts = max(0, state.pending_starts - 1)
        state.pending_memory_mb = max(0.0, state.pending_memory_mb - float(mem_mb or 0.0))
        state.pending_cpu = max(0.0, state.pending_cpu - float(cpu or 0.0))


def commit_quota_reservation(instance: ContainerInstance, mem_mb: float, cpu: float, state: RuntimeStateRefs) -> None:
    with state.state_lock:
        state.pending_starts = max(0, state.pending_starts - 1)
        state.pending_memory_mb = max(0.0, state.pending_memory_mb - float(mem_mb or 0.0))
        state.pending_cpu = max(0.0, state.pending_cpu - float(cpu or 0.0))
        state.active[instance.container_id] = instance
        update_quota_used_unlocked(state)


def sync_from_docker(force: bool = False) -> None:
    global _last_runtime_sync_monotonic
    now_mono = time.monotonic()
    with _state_lock:
        if not force and (now_mono - _last_runtime_sync_monotonic) < 2.0:
            return
    try:
        client = get_runtime_client()
        containers = client.containers.list(filters={"label": TRION_LABEL, "status": "running"})
    except Exception as exc:
        logger.debug("[CommanderDeployState] Runtime sync skipped: %s", exc)
        return

    reconciled: Dict[str, ContainerInstance] = {}
    for container in containers:
        labels = container.labels or {}
        try:
            host_cfg = container.attrs.get("HostConfig", {})
            mem_mb = host_cfg.get("Memory", 0) / (1024 * 1024) or 512.0
            cpu_alloc = round(host_cfg.get("NanoCpus", 0) / 1e9, 2) or 1.0
        except Exception:
            mem_mb, cpu_alloc = 512.0, 1.0
        ttl_secs = int(labels.get("trion.ttl_seconds", "0") or "0")
        expires_epoch = int(labels.get("trion.expires_at", "0") or "0")
        remaining = max(0, expires_epoch - int(time.time())) if expires_epoch > 0 else 0
        reconciled[container.id] = ContainerInstance(
            container_id=container.id,
            blueprint_id=labels.get("trion.blueprint", "unknown"),
            name=container.name,
            status=ContainerStatus.RUNNING,
            started_at=labels.get("trion.started", ""),
            ttl_remaining=remaining if ttl_secs > 0 else 0,
            memory_limit_mb=mem_mb,
            cpu_limit_alloc=cpu_alloc,
            volume_name=labels.get("trion.volume", ""),
            session_id=labels.get("trion.session_id", ""),
        )

    with _state_lock:
        for cid in [item for item in _active if item not in reconciled]:
            timer = _ttl_timers.pop(cid, None)
            if timer:
                try:
                    timer.cancel()
                except Exception:
                    pass
        _active.clear()
        _active.update(reconciled)
        state = build_refs()
        update_quota_used_unlocked(state)
        _last_runtime_sync_monotonic = time.monotonic()


def set_ttl_timer(container_id: str, seconds: int) -> None:
    with _state_lock:
        existing = _ttl_timers.pop(container_id, None)
    if existing:
        existing.cancel()

    def _timeout() -> None:
        logger.warning("[CommanderDeployState] TTL expired for %s, stopping...", container_id[:12])
        emit_ws_activity(
            "container_ttl_expired",
            level="warn",
            message=f"TTL expired for {container_id[:12]}",
            container_id=container_id,
            ttl_seconds=seconds,
        )
        try:
            from mcp.client import call_tool as mcp_call

            blueprint_id, session_id = "unknown", ""
            try:
                container = get_runtime_client().containers.get(container_id)
                container.reload()
                blueprint_id = container.labels.get("trion.blueprint", "unknown")
                session_id = container.labels.get("trion.session_id", "")
            except Exception:
                with _state_lock:
                    instance = _active.get(container_id)
                if instance:
                    blueprint_id, session_id = instance.blueprint_id, instance.session_id
            mcp_call(
                "workspace_event_save",
                {
                    "conversation_id": "_container_events",
                    "event_type": "container_ttl_expired",
                    "event_data": {
                        "container_id": container_id,
                        "blueprint_id": blueprint_id,
                        "session_id": session_id,
                        "expired_at": datetime.utcnow().isoformat() + "Z",
                        "reason": "ttl_expired",
                        "ttl_seconds": seconds,
                    },
                },
            )
        except Exception as exc:
            logger.error("[CommanderDeployState] Failed to write TTL event: %s", exc)
        try:
            stop_container_via_mcp(container_id)
        except Exception as exc:
            logger.error("[CommanderDeployState] Failed to stop expired container %s: %s", container_id[:12], exc)

    timer = threading.Timer(seconds, _timeout)
    timer.daemon = True
    timer.start()
    with _state_lock:
        _ttl_timers[container_id] = timer


def update_quota_used() -> None:
    with _state_lock:
        state = build_refs()
        update_quota_used_unlocked(state)


def recover() -> dict[str, Any]:
    try:
        client = get_runtime_client()
    except Exception as exc:
        logger.error("[CommanderDeployState] Recovery: Docker unavailable: %s", exc)
        return {"recovered": 0, "expired_on_startup": 0, "error": str(exc)}

    try:
        containers = client.containers.list(filters={"label": TRION_LABEL, "status": "running"})
    except Exception as exc:
        return {"recovered": 0, "expired_on_startup": 0, "error": str(exc)}

    recovered, expired = 0, 0
    now_epoch = int(time.time())
    for container in containers:
        container_id = container.id
        with _state_lock:
            if container_id in _active:
                continue

        labels = container.labels or {}
        blueprint_id = labels.get("trion.blueprint", "unknown")
        session_id = labels.get("trion.session_id", "")
        ttl_secs = int(labels.get("trion.ttl_seconds", "0") or "0")
        expires_epoch = int(labels.get("trion.expires_at", "0") or "0")
        remaining = max(0, expires_epoch - now_epoch) if expires_epoch > 0 else 0
        try:
            host_cfg = container.attrs.get("HostConfig", {})
            mem_mb = host_cfg.get("Memory", 0) / (1024 * 1024) or 512.0
            cpu_alloc = round(host_cfg.get("NanoCpus", 0) / 1e9, 2) or 1.0
        except Exception:
            mem_mb, cpu_alloc = 512.0, 1.0

        if ttl_secs > 0 and remaining <= 0:
            logger.warning("[CommanderDeployState] Recovery: %s TTL elapsed — stopping", container_id[:12])
            try:
                from mcp.client import call_tool as mcp_call

                mcp_call(
                    "workspace_event_save",
                    {
                        "conversation_id": "_container_events",
                        "event_type": "container_ttl_expired",
                        "event_data": {
                            "container_id": container_id,
                            "blueprint_id": blueprint_id,
                            "session_id": session_id,
                            "expired_at": datetime.utcnow().isoformat() + "Z",
                            "reason": "ttl_expired_at_startup",
                            "ttl_seconds": ttl_secs,
                        },
                    },
                )
            except Exception:
                pass
            try:
                container.stop(timeout=5)
                container.remove(force=True)
            except Exception as exc:
                logger.error("[CommanderDeployState] Recovery: Stop failed for %s: %s", container_id[:12], exc)
            emit_ws_activity(
                "container_ttl_expired",
                level="warn",
                message=f"TTL expired on startup for {container_id[:12]}",
                container_id=container_id,
                blueprint_id=blueprint_id,
                reason="ttl_expired_at_startup",
                ttl_seconds=ttl_secs,
            )
            expired += 1
            continue

        instance = ContainerInstance(
            container_id=container_id,
            blueprint_id=blueprint_id,
            name=container.name,
            status=ContainerStatus.RUNNING,
            started_at=labels.get("trion.started", ""),
            ttl_remaining=remaining if ttl_secs > 0 else 0,
            memory_limit_mb=mem_mb,
            cpu_limit_alloc=cpu_alloc,
            volume_name=labels.get("trion.volume", ""),
            session_id=session_id,
        )
        with _state_lock:
            _active[container_id] = instance
        if ttl_secs > 0 and remaining > 0:
            set_ttl_timer(container_id, remaining)
        logger.info(
            "[CommanderDeployState] Recovery: registered %s/%s ttl_remaining=%ss",
            blueprint_id,
            container_id[:12],
            remaining,
        )
        recovered += 1

    update_quota_used()
    logger.info(
        "[CommanderDeployState] Recovery: %s recovered, %s expired at startup",
        recovered,
        expired,
    )
    return {"recovered": recovered, "expired_on_startup": expired, "error": None}
