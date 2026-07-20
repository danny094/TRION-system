from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from commander_deploy_runtime_client import TRION_LABEL, TRION_PREFIX, get_runtime_client
from commander_port_manager import validate_port_bindings


logger = logging.getLogger(__name__)

try:
    from docker.errors import APIError, NotFound
except Exception:  # pragma: no cover - lightweight import-only test envs
    class APIError(Exception):
        pass

    class NotFound(Exception):
        pass

SHARED_INTERNAL = "trion-sandbox"
APPROVAL_REQUIRE_BRIDGE = str(os.environ.get("APPROVAL_REQUIRE_BRIDGE", "1")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def parse_memory(mem_str: str) -> int:
    s = str(mem_str or "").strip().lower()
    if s.endswith("g"):
        return int(float(s[:-1]) * 1024 * 1024 * 1024)
    if s.endswith("m"):
        return int(float(s[:-1]) * 1024 * 1024)
    if s.endswith("k"):
        return int(float(s[:-1]) * 1024)
    return int(s)


def ensure_shared_network() -> str:
    client = get_runtime_client()
    try:
        client.networks.get(SHARED_INTERNAL)
    except NotFound:
        client.networks.create(
            SHARED_INTERNAL,
            driver="bridge",
            internal=True,
            labels={TRION_LABEL: "true", "trion.network.type": "internal"},
            options={"com.docker.network.bridge.enable_icc": "true"},
        )
        logger.info("[CommanderDeployRun] Created shared internal network: %s", SHARED_INTERNAL)
    return SHARED_INTERNAL


def resolve_network(mode: Any, container_name: str = "") -> Dict[str, Any]:
    mode_name = str(getattr(mode, "value", mode) or "").strip().lower()
    if mode_name == "none":
        return {
            "network": "none",
            "requires_approval": False,
            "isolation_level": "Full Sandbox — no network",
            "internet_access": False,
        }
    if mode_name == "internal":
        return {
            "network": ensure_shared_network(),
            "requires_approval": False,
            "isolation_level": "Internal — TRION containers only",
            "internet_access": False,
        }
    if mode_name == "bridge":
        return {
            "network": "bridge",
            "requires_approval": APPROVAL_REQUIRE_BRIDGE,
            "isolation_level": "Bridge — host network access",
            "internet_access": False,
        }
    if mode_name == "full":
        return {
            "network": "bridge",
            "requires_approval": True,
            "isolation_level": "Full — internet access enabled",
            "internet_access": True,
        }
    return {
        "network": ensure_shared_network(),
        "requires_approval": False,
        "isolation_level": "Internal (fallback)",
        "internet_access": False,
    }


def start_runtime_container(
    *,
    blueprint_id: str,
    bp: Any,
    resources: Any,
    image_tag: str,
    env_vars: Dict[str, str],
    resume_volume: Optional[str],
    session_id: str,
    conversation_id: str,
    unique_runtime_suffix: Callable[[], str],
    build_port_bindings: Callable,
    build_healthcheck_config: Callable,
) -> Dict[str, Any]:
    client = get_runtime_client()
    unique_suffix = unique_runtime_suffix()
    container_name = f"{TRION_PREFIX}{blueprint_id}_{unique_suffix}"
    volume_name = resume_volume if resume_volume else f"trion_ws_{blueprint_id}_{unique_suffix}"

    created_workspace_volume = not bool(resume_volume)
    if created_workspace_volume:
        client.volumes.create(name=volume_name, labels={TRION_LABEL: "true"})

    volumes = {volume_name: {"bind": "/workspace", "mode": "rw"}}
    for mount in bp.mounts:
        mount_type = str(getattr(mount, "type", "bind") or "bind").strip().lower()
        host_path = mount.host if mount_type == "volume" else os.path.abspath(mount.host)
        volumes[host_path] = {"bind": mount.container, "mode": mount.mode}

    net_info = resolve_network(bp.network, container_name)
    network_mode = net_info["network"]

    mem_bytes = parse_memory(resources.memory_limit)
    swap_bytes = parse_memory(resources.memory_swap)
    try:
        port_bindings = build_port_bindings(bp.ports)
    except ValueError as exc:
        raise RuntimeError(f"invalid_port_mapping: {exc}") from exc
    healthcheck = build_healthcheck_config(bp.healthcheck)
    if port_bindings:
        conflicts = validate_port_bindings(port_bindings)
        if conflicts:
            details = ", ".join(
                f"{c.get('host_port')}/{c.get('protocol')} ({c.get('reason', 'occupied')})" for c in conflicts[:3]
            )
            raise RuntimeError(f"port_conflict_precheck_failed: {details}")

    ttl_secs = resources.timeout_seconds
    expires_epoch = (int(time.time()) + ttl_secs) if ttl_secs > 0 else 0
    run_kwargs = {
        "image": image_tag,
        "detach": True,
        "name": container_name,
        "environment": env_vars,
        "volumes": volumes,
        "network": network_mode,
        "labels": {
            TRION_LABEL: "true",
            "trion.blueprint": blueprint_id,
            "trion.image_tag": image_tag,
            "trion.volume": volume_name,
            "trion.started": datetime.utcnow().isoformat(),
            "trion.session_id": session_id or "",
            "trion.conversation_id": conversation_id or "",
            "trion.port_bindings": json.dumps(port_bindings) if port_bindings else "",
            "trion.ttl_seconds": str(ttl_secs),
            "trion.expires_at": str(expires_epoch),
        },
        "cpu_period": 100000,
        "cpu_quota": int(float(resources.cpu_limit) * 100000),
        "mem_limit": mem_bytes,
        "memswap_limit": swap_bytes,
        "pids_limit": resources.pids_limit,
        "stdin_open": True,
        "tty": False,
        "auto_remove": False,
    }
    if port_bindings:
        run_kwargs["ports"] = port_bindings
    if bp.runtime:
        run_kwargs["runtime"] = bp.runtime
    if bp.devices:
        run_kwargs["devices"] = list(bp.devices)
    if bp.cap_add:
        run_kwargs["cap_add"] = list(bp.cap_add)
    if bp.security_opt:
        run_kwargs["security_opt"] = list(bp.security_opt)
    if bp.cap_drop:
        run_kwargs["cap_drop"] = list(bp.cap_drop)
    if bp.privileged:
        run_kwargs["privileged"] = True
    if bp.read_only_rootfs:
        run_kwargs["read_only"] = True
    if bp.shm_size:
        run_kwargs["shm_size"] = bp.shm_size
    if bp.ipc_mode:
        run_kwargs["ipc_mode"] = bp.ipc_mode
    if healthcheck:
        run_kwargs["healthcheck"] = healthcheck

    try:
        container = client.containers.run(**run_kwargs)
    except APIError as exc:
        if created_workspace_volume:
            try:
                client.volumes.get(volume_name).remove()
            except Exception:
                pass
        raise RuntimeError(f"Container start failed: {exc}") from exc

    return {
        "client": client,
        "container": container,
        "container_name": container_name,
        "volume_name": volume_name,
        "created_workspace_volume": created_workspace_volume,
        "mem_bytes": mem_bytes,
        "net_info": net_info,
        "healthcheck": healthcheck,
    }
