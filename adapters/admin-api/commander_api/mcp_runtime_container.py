from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException


RuntimeCall = Callable[..., dict[str, Any]]


def list_containers_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> list[dict[str, Any]]:
    result = call_runtime_tool("container_list", {}, timeout=timeout)
    containers = result.get("containers")
    return list(containers) if isinstance(containers, list) else []


def inspect_container_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, timeout: float) -> dict[str, Any]:
    result = call_runtime_tool("container_inspect", {"container_id": container_id}, timeout=timeout)
    container = result.get("container")
    if not isinstance(container, dict):
        raise HTTPException(status_code=502, detail="invalid_container_inspect_result")
    return container


def get_container_logs_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, tail: int, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("container_logs", {"container_id": container_id, "tail": int(tail)}, timeout=timeout)


def get_container_stats_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("container_stats", {"container_id": container_id}, timeout=timeout)


def get_runtime_quota_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("runtime_quota", {}, timeout=timeout)


def exec_in_container_via_mcp(
    call_runtime_tool: RuntimeCall,
    container_id: str,
    command: str,
    *,
    timeout: int,
    rpc_timeout: float,
) -> dict[str, Any]:
    return call_runtime_tool(
        "container_exec",
        {"container_id": container_id, "command": command, "timeout": int(timeout)},
        timeout=rpc_timeout,
    )


def exec_in_container_detailed_via_mcp(
    call_runtime_tool: RuntimeCall,
    container_id: str,
    command: str,
    *,
    timeout: int,
    rpc_timeout: float,
) -> dict[str, Any]:
    return call_runtime_tool(
        "container_exec_detailed",
        {"container_id": container_id, "command": command, "timeout": int(timeout)},
        timeout=rpc_timeout,
    )


def cleanup_all_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("runtime_cleanup_all", {}, timeout=timeout)


def remove_stopped_container_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("remove_stopped_container", {"container_id": container_id}, timeout=timeout)


def start_container_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("start_stopped_container", {"container_id": container_id}, timeout=timeout)


def stop_container_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("stop_container", {"container_id": container_id}, timeout=timeout)


def evaluate_home_status_via_mcp(
    list_containers: Callable[..., list[dict[str, Any]]],
    inspect_container: Callable[..., dict[str, Any]],
    *,
    timeout: float,
) -> dict[str, Any]:
    containers = list_containers(timeout=timeout)
    if not containers:
        return {"status": "offline", "error_code": "home_not_found"}
    candidates = sorted(containers, key=lambda item: 0 if str(item.get("name") or "").strip() == "trion-home" else 1)
    for item in candidates:
        container_id = str(item.get("container_id") or "").strip()
        if not container_id:
            continue
        try:
            details = inspect_container(container_id, timeout=timeout)
        except HTTPException:
            continue
        home_scope = details.get("home_scope")
        if not isinstance(home_scope, dict) or not bool(home_scope.get("is_home")):
            continue
        return {
            "status": str(details.get("status") or "unknown"),
            "error_code": "",
            "home_container_id": container_id,
            "identity_path": str(home_scope.get("home_root") or ""),
        }
    return {"status": "offline", "error_code": "home_not_found"}
