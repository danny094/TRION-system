#!/usr/bin/env python3
import os

import bundle_docker
from bundle_common import container_summary, error_result, is_not_found, managed_flags, port_rows, resolve_container_reference
from bundle_home import blueprint_id_from_labels, build_home_scope, read_home_manifest


def list_containers():
    try:
        client = bundle_docker.get_docker_client()
        containers = client.containers.list(all=True)
        return {"containers": [container_summary(container) for container in containers]}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def inspect_container(container_id="", container_name=""):
    container_ref = container_id
    try:
        client = bundle_docker.get_docker_client()
        container = resolve_container_reference(client, container_ref)
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
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_logs(container_id="", tail=200, since="", limit_chars=16000, container_name=""):
    container_ref = container_id
    safe_tail = max(1, min(int(tail), 500))
    safe_limit = max(256, min(int(limit_chars), 64000))
    try:
        client = bundle_docker.get_docker_client()
        container = resolve_container_reference(client, container_ref)
        raw = container.logs(tail=safe_tail, timestamps=True, since=since or None)
        logs = raw.decode("utf-8", errors="replace")
        truncated = len(logs) > safe_limit
        if truncated:
            logs = logs[-safe_limit:]
        return {
            "container_id": container_ref,
            "logs": logs,
            "truncated": truncated,
            "tail": safe_tail,
            "since": str(since or ""),
            "limit_chars": safe_limit,
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_container_stats(container_id="", container_name=""):
    container_ref = container_id
    try:
        client = bundle_docker.get_docker_client()
        container = resolve_container_reference(client, container_ref)
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
            "container_id": container_ref,
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
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
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

        client = bundle_docker.get_docker_client()
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
