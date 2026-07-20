"""
Shared volume compatibility helpers.

This module is the local truth for the remaining legacy
`container_commander.volumes` public wrapper surface.
"""

from __future__ import annotations

from commander_volume_runtime import (
    cleanup_orphaned_volumes_via_mcp,
    create_snapshot_via_mcp,
    create_volume,
    delete_snapshot_via_mcp,
    get_volume_via_mcp,
    list_snapshots_via_mcp,
    list_volumes_via_mcp,
    remove_volume_via_mcp,
    restore_snapshot_via_mcp,
)


def list_volumes(blueprint_id: str = ""):
    return list_volumes_via_mcp(blueprint_id=blueprint_id or "")


def get_volume(volume_name: str):
    try:
        return get_volume_via_mcp(volume_name)
    except Exception:
        return None


def remove_volume(volume_name: str, force: bool = False) -> bool:
    return remove_volume_via_mcp(volume_name, force=bool(force))


def find_latest_volume(blueprint_id: str):
    volumes = list_volumes(blueprint_id=blueprint_id)
    if volumes:
        return str(volumes[0].get("name") or "") or None
    return None


def cleanup_orphaned_volumes(dry_run: bool = True):
    return cleanup_orphaned_volumes_via_mcp(dry_run=bool(dry_run))


def create_snapshot(volume_name: str, tag: str = ""):
    return create_snapshot_via_mcp(volume_name, tag=tag or "")


def restore_snapshot(snapshot_filename: str, target_volume: str = ""):
    volume_name = restore_snapshot_via_mcp(snapshot_filename, target_volume=target_volume or "")
    return volume_name or None


def list_snapshots(volume_name: str = ""):
    return list_snapshots_via_mcp(volume_name=volume_name or "")


def delete_snapshot(filename: str) -> bool:
    return delete_snapshot_via_mcp(filename)
