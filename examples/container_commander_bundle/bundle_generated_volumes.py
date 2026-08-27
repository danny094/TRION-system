#!/usr/bin/env python3

from bundle_snapshots import list_snapshots, delete_snapshot, create_snapshot, restore_snapshot
from bundle_volumes import list_volumes, get_volume, remove_volume, cleanup_orphaned_volumes

def volume_list(blueprint_id: str = "") -> dict:
    """List TRION-managed workspace volumes."""
    return list_volumes(blueprint_id)

def volume_get(volume_name: str) -> dict:
    """Get one volume with snapshot metadata."""
    return get_volume(volume_name)

def volume_remove(volume_name: str, force: bool = False) -> dict:
    """Remove one workspace volume."""
    return remove_volume(volume_name, force=force)

def volume_cleanup(dry_run: bool = True) -> dict:
    """Find and optionally remove orphaned workspace volumes."""
    return cleanup_orphaned_volumes(dry_run=dry_run)

def snapshot_list(volume_name: str = "") -> dict:
    """List snapshots, optionally filtered by volume prefix."""
    return list_snapshots(volume_name)

def snapshot_delete(filename: str) -> dict:
    """Delete one stored snapshot tarball."""
    return delete_snapshot(filename)

def snapshot_create(volume_name: str, tag: str = "") -> dict:
    """Create one snapshot tarball for a workspace volume."""
    return create_snapshot(volume_name, tag=tag)

def snapshot_restore(filename: str, target_volume: str = "") -> dict:
    """Restore one snapshot tarball into a target or derived volume."""
    return restore_snapshot(filename, target_volume=target_volume)
