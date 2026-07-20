"""
Commander port management utilities.

Local truth for deploy-time port checks and host port inspection helpers.
"""

from __future__ import annotations

import json
import logging
import socket
from typing import Dict, List, Tuple

try:
    import docker  # type: ignore
except Exception:  # pragma: no cover - optional in lightweight test envs
    docker = None

logger = logging.getLogger(__name__)


def _iter_proc_ports(proc_path: str, protocol: str, listen_states: set[str]) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(proc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[1:]
    except Exception:
        return rows

    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue
        state = parts[3]
        if listen_states and state not in listen_states:
            continue
        local = parts[1]
        try:
            port = int(local.split(":")[1], 16)
        except Exception:
            continue
        rows.append({"port": port, "protocol": protocol, "source": "proc"})
    return rows


def list_used_ports(include_udp: bool = True) -> List[dict]:
    rows: List[dict] = []
    rows.extend(_iter_proc_ports("/proc/net/tcp", "tcp", {"0A"}))
    rows.extend(_iter_proc_ports("/proc/net/tcp6", "tcp", {"0A"}))
    if include_udp:
        rows.extend(_iter_proc_ports("/proc/net/udp", "udp", {"07", "0A"}))
        rows.extend(_iter_proc_ports("/proc/net/udp6", "udp", {"07", "0A"}))

    dedup = {(row["port"], row["protocol"]): row for row in rows}
    return sorted(dedup.values(), key=lambda row: (row["port"], row["protocol"]))


def check_port(port: int, protocol: str = "tcp") -> Tuple[bool, str]:
    proto = str(protocol or "tcp").lower()
    family = socket.AF_INET
    sock_type = socket.SOCK_DGRAM if proto == "udp" else socket.SOCK_STREAM
    sock = socket.socket(family, sock_type)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", int(port)))
        return True, "free"
    except OSError as exc:
        return False, str(exc)
    finally:
        try:
            sock.close()
        except Exception:
            pass


def find_free_port(
    min_port: int = 8000,
    max_port: int = 9000,
    protocol: str = "tcp",
    excluded_ports: set[int] | None = None,
) -> int:
    excluded = excluded_ports or set()
    for port in range(int(min_port), int(max_port) + 1):
        if port in excluded:
            continue
        ok, _ = check_port(port, protocol=protocol)
        if ok:
            return port
    raise RuntimeError(f"no free {protocol} port found in range {min_port}-{max_port}")


def _expand_host_port_token(token: str) -> List[int]:
    token = str(token or "").strip()
    if not token:
        return []
    if "-" in token:
        start_str, end_str = token.split("-", 1)
        start = int(start_str.strip())
        end = int(end_str.strip())
        if end < start:
            raise ValueError(f"invalid port range '{token}'")
        return list(range(start, end + 1))
    return [int(token)]


def validate_port_bindings(port_bindings: Dict[str, str]) -> List[dict]:
    conflicts: List[dict] = []
    for container_key, host_value in dict(port_bindings or {}).items():
        proto = "tcp"
        if "/" in container_key:
            _, proto = container_key.rsplit("/", 1)
        try:
            host_ports = _expand_host_port_token(str(host_value))
        except Exception as exc:
            conflicts.append(
                {
                    "host_port": host_value,
                    "protocol": proto,
                    "container": container_key,
                    "reason": f"invalid_host_port: {exc}",
                }
            )
            continue

        for host_port in host_ports:
            ok, reason = check_port(host_port, protocol=proto)
            if not ok:
                conflicts.append(
                    {
                        "host_port": host_port,
                        "protocol": proto,
                        "container": container_key,
                        "reason": reason,
                    }
                )
    return conflicts


def list_blueprint_ports() -> List[dict]:
    if docker is None:
        return []
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True, filters={"label": "trion.managed=true"})
    except Exception as exc:
        logger.debug("[PortManager] Docker unavailable for list_blueprint_ports: %s", exc)
        return []

    result: List[dict] = []
    for container in containers:
        labels = container.labels or {}
        raw = labels.get("trion.port_bindings", "").strip()
        parsed = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {}
        if not parsed:
            parsed = {}
            try:
                ports_obj = ((container.attrs or {}).get("NetworkSettings", {}) or {}).get("Ports", {}) or {}
                for container_port, bindings in ports_obj.items():
                    if not bindings:
                        continue
                    host_port = bindings[0].get("HostPort", "")
                    if host_port:
                        parsed[container_port] = str(host_port)
            except Exception:
                parsed = {}

        result.append(
            {
                "container_id": container.id,
                "name": container.name,
                "blueprint_id": labels.get("trion.blueprint", "unknown"),
                "status": container.status,
                "ports": parsed,
            }
        )
    return result
