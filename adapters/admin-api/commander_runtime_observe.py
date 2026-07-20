from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

try:
    from docker.errors import NotFound
except Exception:  # pragma: no cover - lightweight import-only test envs
    class NotFound(Exception):
        pass

from commander_deploy_runtime_client import get_runtime_client
from commander_deploy_runtime_state import build_refs
from commander_runtime_connection import extract_port_details, merge_host_companion_access_info
from models import ContainerInstance, ContainerStatus


logger = logging.getLogger(__name__)


def get_container_logs(container_id: str, tail: int = 100) -> str:
    client = get_runtime_client()
    try:
        return client.containers.get(container_id).logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
    except NotFound:
        return "Container not found"
    except Exception as exc:
        return f"Error: {exc}"


def get_container_stats(container_id: str) -> Dict:
    client = get_runtime_client()
    state = build_refs()
    try:
        container = client.containers.get(container_id)
        attrs = container.attrs or {}
        stats = container.stats(stream=False)
        network_settings = attrs.get("NetworkSettings", {})
        networks = network_settings.get("Networks", {})
        ip_address = next((value.get("IPAddress") for value in networks.values() if value.get("IPAddress")), None)
        blueprint_id = container.labels.get("trion.blueprint", "unknown")
        ports = extract_port_details(attrs)
        ports, connection = merge_host_companion_access_info(blueprint_id, ip_address, ports)

        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0
        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 1)
        mem_mb = mem_usage / (1024 * 1024)
        net_rx = sum(value.get("rx_bytes", 0) for value in stats.get("networks", {}).values())
        net_tx = sum(value.get("tx_bytes", 0) for value in stats.get("networks", {}).values())

        instance = None
        with state.state_lock:
            instance = state.active.get(container_id)
            if instance:
                instance.cpu_percent = round(cpu_percent, 1)
                instance.memory_mb = round(mem_mb, 1)
                instance.network_rx_bytes = net_rx
                instance.network_tx_bytes = net_tx
                if instance.started_at:
                    instance.runtime_seconds = int(
                        (datetime.utcnow() - datetime.fromisoformat(instance.started_at)).total_seconds()
                    )
                instance.efficiency_score, instance.efficiency_level = _calc_efficiency(instance)

        return {
            "container_id": container_id,
            "cpu_percent": round(cpu_percent, 1),
            "memory_mb": round(mem_mb, 1),
            "memory_limit_mb": round(mem_limit / (1024 * 1024), 1),
            "network_rx_bytes": net_rx,
            "network_tx_bytes": net_tx,
            "ports": ports,
            "connection": connection,
            "efficiency": {
                "score": instance.efficiency_score if instance else 0,
                "level": instance.efficiency_level if instance else "green",
            },
            "deploy_warnings": list(instance.deploy_warnings or []) if instance else [],
        }
    except NotFound:
        return {"error": "Container not found"}
    except Exception as exc:
        return {"error": str(exc)}


def list_containers() -> List[ContainerInstance]:
    client = get_runtime_client()
    state = build_refs()
    result: List[ContainerInstance] = []
    try:
        with state.state_lock:
            active_snapshot = dict(state.active)
        containers = client.containers.list(all=True, filters={"label": "trion.managed"})
        for container in containers:
            blueprint_id = container.labels.get("trion.blueprint", "unknown")
            status = (
                ContainerStatus.RUNNING
                if container.status == "running"
                else ContainerStatus.STOPPED
                if container.status in ("exited", "dead")
                else ContainerStatus.ERROR
            )
            instance = active_snapshot.get(
                container.id,
                ContainerInstance(
                    container_id=container.id,
                    blueprint_id=blueprint_id,
                    name=container.name,
                    status=status,
                    started_at=container.labels.get("trion.started", ""),
                    volume_name=container.labels.get("trion.volume", ""),
                ),
            )
            instance.status = status
            result.append(instance)
    except Exception as exc:
        logger.error("[CommanderObserve] List containers failed: %s", exc)
    return result


def inspect_container(container_id: str) -> Dict:
    client = get_runtime_client()
    state_refs = build_refs()
    try:
        container = client.containers.get(container_id)
        attrs = container.attrs
        state = attrs.get("State", {})
        health_state = state.get("Health") or {}
        config = attrs.get("Config", {})
        host_config = attrs.get("HostConfig", {})
        networks = (attrs.get("NetworkSettings") or {}).get("Networks", {})
        ip_address = next((value.get("IPAddress") for value in networks.values() if value.get("IPAddress")), None)
        mem_bytes = host_config.get("Memory", 0)
        nano_cpus = host_config.get("NanoCpus", 0)
        blueprint_id = container.labels.get("trion.blueprint", "unknown")
        ports = extract_port_details(attrs)
        ports, connection = merge_host_companion_access_info(blueprint_id, ip_address, ports)
        mounts = [
            f"{mount.get('Source', '?')}:{mount.get('Destination', '?')}"
            for mount in attrs.get("Mounts", [])
            if mount.get("Type") == "volume"
        ]
        with state_refs.state_lock:
            in_memory = state_refs.active.get(container.id)
        return {
            "container_id": container.id,
            "short_id": container.short_id,
            "name": container.name,
            "blueprint_id": blueprint_id,
            "image": config.get("Image", ""),
            "status": state.get("Status", "unknown"),
            "health_status": health_state.get("Status", ""),
            "running": state.get("Running", False),
            "exit_code": state.get("ExitCode") if not state.get("Running") else None,
            "started_at": state.get("StartedAt", ""),
            "finished_at": state.get("FinishedAt", "") if not state.get("Running") else None,
            "ip_address": ip_address,
            "ports": ports,
            "connection": connection,
            "network": list(networks.keys())[0] if networks else None,
            "mounts": mounts,
            "resource_limits": {
                "memory_mb": round(mem_bytes / (1024 * 1024), 1) if mem_bytes else None,
                "cpu_count": round(nano_cpus / 1e9, 2) if nano_cpus else None,
            },
            "ttl_remaining_seconds": int(in_memory.ttl_remaining) if in_memory and in_memory.ttl_remaining else None,
            "volume": container.labels.get("trion.volume", ""),
            "deploy_warnings": list(in_memory.deploy_warnings or []) if in_memory else [],
        }
    except Exception as exc:
        logger.error("[CommanderObserve] Inspect failed (%s): %s", container_id, exc)
        return {"error": str(exc), "container_id": container_id}


def _calc_efficiency(instance: ContainerInstance):
    runtime = instance.runtime_seconds
    cpu = instance.cpu_percent
    mem_pct = (instance.memory_mb / instance.memory_limit_mb * 100) if instance.memory_limit_mb > 0 else 0
    score = 1.0
    if runtime > 300 and cpu < 1.0:
        score -= 0.3
    elif runtime > 600 and cpu < 5.0:
        score -= 0.5
    if mem_pct > 80 and cpu < 2.0:
        score -= 0.2
    score = max(0.0, min(1.0, score))
    level = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
    return round(score, 2), level
