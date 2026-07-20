from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from commander_api.mcp_runtime import (
    cleanup_all_via_mcp,
    exec_in_container_detailed_via_mcp,
    exec_in_container_via_mcp,
    get_container_logs_via_mcp,
    get_container_stats_via_mcp,
    get_runtime_quota_via_mcp,
)
from commander_runtime_models import SessionQuota

logger = logging.getLogger(__name__)


def exec_in_container(container_id: str, command: str, timeout: int = 30) -> tuple[int, str]:
    result = exec_in_container_via_mcp(container_id, command, timeout=timeout)
    return int(result.get("exit_code", -1) or -1), str(result.get("output") or "")


def exec_in_container_detailed(container_id: str, command: str, timeout: int = 30) -> dict[str, Any]:
    return exec_in_container_detailed_via_mcp(container_id, command, timeout=timeout)
def get_container_logs(container_id: str, tail: int = 100) -> str:
    result = get_container_logs_via_mcp(container_id, tail=tail)
    return str(result.get("logs") or "")


def get_container_stats(container_id: str) -> dict[str, Any]:
    return get_container_stats_via_mcp(container_id)


def get_quota() -> SessionQuota:
    return SessionQuota(**get_runtime_quota_via_mcp())


def cleanup_all() -> None:
    cleanup_all_via_mcp()
