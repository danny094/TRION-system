"""Shared runtime stop/start compatibility helpers."""

from __future__ import annotations

from commander_api.mcp_runtime import start_container_via_mcp, stop_container_via_mcp
from commander_container_lifecycle import remove_stopped_container as remove_stopped_container_local


def stop_container(container_id: str, remove=None) -> bool:
    _ = remove
    result = stop_container_via_mcp(container_id)
    return bool(result.get("stopped"))


def remove_stopped_container(container_id: str) -> dict:
    return remove_stopped_container_local(container_id)


def start_stopped_container(container_id: str) -> bool:
    result = start_container_via_mcp(container_id)
    return bool(result.get("started") or result.get("action") == "already_running")
