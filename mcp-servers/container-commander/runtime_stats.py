from __future__ import annotations

from typing import Any


def stats_payload(container_id: str, attrs: dict[str, Any], stats: dict[str, Any], ports: list[dict[str, str]]) -> dict[str, Any]:
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
        "ports": ports,
        "efficiency": {"score": round(score, 2), "level": level},
        "deploy_warnings": [],
    }
