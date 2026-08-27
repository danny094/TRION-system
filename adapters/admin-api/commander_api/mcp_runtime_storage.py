from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException


RuntimeCall = Callable[..., dict[str, Any]]


def list_volumes_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> list[dict[str, Any]]:
    result = call_runtime_tool("volume_list", {"blueprint_id": blueprint_id} if blueprint_id else {}, timeout=timeout)
    volumes = result.get("volumes")
    return list(volumes) if isinstance(volumes, list) else []


def get_volume_via_mcp(call_runtime_tool: RuntimeCall, volume_name: str, *, timeout: float) -> dict[str, Any]:
    result = call_runtime_tool("volume_get", {"volume_name": volume_name}, timeout=timeout)
    volume = result.get("volume")
    if not isinstance(volume, dict):
        raise HTTPException(status_code=502, detail="invalid_volume_get_result")
    return volume


def remove_volume_via_mcp(call_runtime_tool: RuntimeCall, volume_name: str, *, force: bool, timeout: float) -> bool:
    result = call_runtime_tool("volume_remove", {"volume_name": volume_name, "force": bool(force)}, timeout=timeout)
    return bool(result.get("removed"))


def cleanup_orphaned_volumes_via_mcp(call_runtime_tool: RuntimeCall, *, dry_run: bool, timeout: float) -> list[str]:
    result = call_runtime_tool("volume_cleanup", {"dry_run": bool(dry_run)}, timeout=timeout)
    orphaned = result.get("orphaned")
    return list(orphaned) if isinstance(orphaned, list) else []


def list_snapshots_via_mcp(call_runtime_tool: RuntimeCall, volume_name: str, *, timeout: float) -> list[dict[str, Any]]:
    result = call_runtime_tool("snapshot_list", {"volume_name": volume_name} if volume_name else {}, timeout=timeout)
    snapshots = result.get("snapshots")
    return list(snapshots) if isinstance(snapshots, list) else []


def delete_snapshot_via_mcp(call_runtime_tool: RuntimeCall, filename: str, *, timeout: float) -> bool:
    result = call_runtime_tool("snapshot_delete", {"filename": filename}, timeout=timeout)
    return bool(result.get("deleted"))


def create_snapshot_via_mcp(call_runtime_tool: RuntimeCall, volume_name: str, *, tag: str, timeout: float) -> str:
    result = call_runtime_tool("snapshot_create", {"volume_name": volume_name, "tag": tag}, timeout=timeout)
    if not bool(result.get("created")):
        return ""
    filename = result.get("filename")
    return str(filename) if isinstance(filename, str) else ""


def restore_snapshot_via_mcp(
    call_runtime_tool: RuntimeCall,
    filename: str,
    *,
    target_volume: str,
    timeout: float,
) -> str:
    result = call_runtime_tool(
        "snapshot_restore",
        {"filename": filename, "target_volume": target_volume},
        timeout=timeout,
    )
    if not bool(result.get("restored")):
        return ""
    volume = result.get("volume")
    return str(volume) if isinstance(volume, str) else ""
