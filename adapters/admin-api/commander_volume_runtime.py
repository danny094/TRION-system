"""
Commander volume runtime helpers.

Local truth for the remaining volume create/latest helpers plus MCP-backed
volume and snapshot accessors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from commander_api.mcp_runtime import (
    cleanup_orphaned_volumes_via_mcp,
    create_snapshot_via_mcp,
    delete_snapshot_via_mcp,
    get_volume_via_mcp,
    list_snapshots_via_mcp,
    list_volumes_via_mcp,
    remove_volume_via_mcp,
    restore_snapshot_via_mcp,
)
from commander_deploy_runtime_client import TRION_LABEL, get_runtime_client


def create_volume(blueprint_id: str, session_id: Optional[str] = None) -> str:
    client = get_runtime_client()
    ts = session_id or str(int(datetime.now(timezone.utc).timestamp()))
    name = f"trion_ws_{blueprint_id}_{ts}"
    client.volumes.create(
        name=name,
        driver="local",
        labels={
            TRION_LABEL: "true",
            "trion.blueprint": blueprint_id,
            "trion.created": datetime.now(timezone.utc).isoformat(),
        },
    )
    return name


def list_volumes(blueprint_id: Optional[str] = None) -> List[Dict]:
    return list_volumes_via_mcp(blueprint_id=blueprint_id or "")


def get_volume(volume_name: str) -> Optional[Dict]:
    try:
        return get_volume_via_mcp(volume_name)
    except Exception:
        return None


def remove_volume(volume_name: str, force: bool = False) -> bool:
    return remove_volume_via_mcp(volume_name, force=bool(force))


def find_latest_volume(blueprint_id: str) -> Optional[str]:
    volumes = list_volumes(blueprint_id=blueprint_id)
    if volumes:
        return str(volumes[0].get("name") or "") or None
    return None


def cleanup_orphaned_volumes(dry_run: bool = True) -> List[str]:
    return cleanup_orphaned_volumes_via_mcp(dry_run=bool(dry_run))


def create_snapshot(volume_name: str, tag: Optional[str] = None) -> Optional[str]:
    filename = create_snapshot_via_mcp(volume_name, tag=tag or "")
    return filename or None


def restore_snapshot(snapshot_filename: str, target_volume: Optional[str] = None) -> Optional[str]:
    volume_name = restore_snapshot_via_mcp(snapshot_filename, target_volume=target_volume or "")
    return volume_name or None


def list_snapshots(volume_name: Optional[str] = None) -> List[Dict]:
    return list_snapshots_via_mcp(volume_name=volume_name or "")


def delete_snapshot(filename: str) -> bool:
    return delete_snapshot_via_mcp(filename)
