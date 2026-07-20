from __future__ import annotations

import logging
import threading
from typing import Any

from commander_ws_activity import emit_activity

TRION_LABEL = "trion.managed"
TRION_PREFIX = "trion_"
NETWORK_NAME = "trion-sandbox"

logger = logging.getLogger(__name__)

try:
    import docker
    from docker.errors import NotFound
except Exception:  # pragma: no cover - lightweight import-only test envs
    docker = None

    class NotFound(Exception):
        pass


_client: Any = None
_client_lock = threading.Lock()


def emit_ws_activity(event: str, level: str = "info", message: str = "", **data: Any) -> None:
    emit_activity(event, level=level, message=message, **data)


def get_runtime_client() -> Any:
    global _client
    if _client is None:
        if docker is None:
            raise RuntimeError("docker_runtime_unavailable")
        with _client_lock:
            if _client is None:
                _client = docker.from_env()
                _ensure_network()
    return _client


def _ensure_network() -> None:
    try:
        _client.networks.get(NETWORK_NAME)
    except NotFound:
        _client.networks.create(
            NETWORK_NAME,
            driver="bridge",
            internal=True,
            labels={TRION_LABEL: "true"},
        )
        logger.info("[CommanderDeployRuntimeClient] Created network: %s", NETWORK_NAME)


def validate_runtime_preflight(client: Any, runtime: str) -> tuple[bool, str]:
    rt = str(runtime or "").strip().lower()
    if not rt or rt != "nvidia":
        return True, "ok"
    try:
        info = client.info() if hasattr(client, "info") else client.api.info()
    except Exception as exc:
        return False, f"runtime_preflight_failed: cannot query docker info ({exc})"
    if "nvidia" in dict((info or {}).get("Runtimes") or {}):
        return True, "ok"
    return False, "nvidia_runtime_unavailable: Docker runtime 'nvidia' not found. Install/enable NVIDIA Container Toolkit."
