import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from .common import exception_response
from .mcp_runtime import (
    cleanup_orphaned_volumes_via_mcp,
    cleanup_networks_via_mcp,
    create_snapshot_via_mcp,
    delete_snapshot_via_mcp,
    get_network_info_via_mcp,
    get_volume_via_mcp,
    list_networks_via_mcp,
    list_snapshots_via_mcp,
    list_volumes_via_mcp,
    remove_volume_via_mcp,
    restore_snapshot_via_mcp,
)

router = APIRouter()


def _managed_path_catalog(paths: list[str]) -> list[dict]:
    catalog = []
    seen = set()
    for raw in list(paths or []):
        p = os.path.abspath(str(raw or "").strip())
        if not p or p in seen:
            continue
        seen.add(p)
        base = os.path.basename(p.rstrip("/")) or p
        catalog.append(
            {
                "id": f"mp:{base}:{len(catalog) + 1}",
                "label": base,
                "path": p,
                "source": "storage_broker",
            }
        )
    catalog.sort(key=lambda item: item["path"])
    return catalog


@router.get("/volumes")
async def api_list_volumes(blueprint_id: Optional[str] = None):
    """List all TRION workspace volumes."""
    try:
        vols = list_volumes_via_mcp(blueprint_id=blueprint_id or "")
        return {"volumes": vols, "count": len(vols)}
    except Exception as e:
        return exception_response(e)


@router.get("/volumes/{volume_name}")
async def api_get_volume(volume_name: str):
    """Get details of a specific volume including its snapshots."""
    try:
        return {"volume": get_volume_via_mcp(volume_name)}
    except Exception as e:
        return exception_response(e)


@router.delete("/volumes/{volume_name}")
async def api_remove_volume(volume_name: str, force: bool = False):
    """Remove a workspace volume."""
    try:
        removed = remove_volume_via_mcp(volume_name, force=force)
        if not removed:
            return exception_response(
                HTTPException(404, f"Volume '{volume_name}' not found or in use"),
                error_code="not_found",
                details={"removed": False, "volume": volume_name},
            )
        return {"removed": True, "volume": volume_name}
    except Exception as e:
        return exception_response(e)


@router.post("/volumes/cleanup")
async def api_cleanup_volumes(dry_run: bool = True):
    """Find and optionally remove orphaned volumes."""
    try:
        orphaned = cleanup_orphaned_volumes_via_mcp(dry_run=dry_run)
        return {"orphaned": orphaned, "count": len(orphaned), "dry_run": dry_run}
    except Exception as e:
        return exception_response(e)


@router.get("/snapshots")
async def api_list_snapshots(volume_name: Optional[str] = None):
    """List all snapshots, optionally filtered by volume."""
    try:
        snaps = list_snapshots_via_mcp(volume_name=volume_name or "")
        return {"snapshots": snaps, "count": len(snaps)}
    except Exception as e:
        return exception_response(e)


@router.post("/snapshots/create")
async def api_create_snapshot(request: Request):
    """Create a tarball snapshot of a volume."""
    try:
        data = await request.json()
        volume_name = data.get("volume_name", "")
        tag = data.get("tag", "")
        if not volume_name:
            return exception_response(
                HTTPException(400, "'volume_name' is required"),
                error_code="bad_request",
                details={"created": False},
            )
        filename = create_snapshot_via_mcp(volume_name, tag=tag or "")
        if not filename:
            return exception_response(
                RuntimeError("Snapshot failed"),
                error_code="snapshot_failed",
                details={"created": False},
            )
        return {"created": True, "filename": filename}
    except Exception as e:
        return exception_response(e)


@router.post("/snapshots/restore")
async def api_restore_snapshot(request: Request):
    """Restore a snapshot into a new or existing volume."""
    try:
        data = await request.json()
        filename = data.get("filename", "")
        target = data.get("target_volume")
        if not filename:
            return exception_response(
                HTTPException(400, "'filename' is required"),
                error_code="bad_request",
                details={"restored": False},
            )
        vol_name = restore_snapshot_via_mcp(filename, target_volume=target or "")
        if not vol_name:
            return exception_response(
                RuntimeError("Restore failed"),
                error_code="restore_failed",
                details={"restored": False},
            )
        return {"restored": True, "volume": vol_name}
    except Exception as e:
        return exception_response(e)


@router.delete("/snapshots/{filename}")
async def api_delete_snapshot(filename: str):
    """Delete a snapshot file."""
    try:
        deleted = delete_snapshot_via_mcp(filename)
        if not deleted:
            return exception_response(
                HTTPException(404, f"Snapshot '{filename}' not found"),
                error_code="not_found",
                details={"deleted": False, "filename": filename},
            )
        return {"deleted": True, "filename": filename}
    except Exception as e:
        return exception_response(e)


@router.get("/networks")
async def api_list_networks():
    """List all TRION-managed Docker networks."""
    try:
        nets = list_networks_via_mcp()
        return {"networks": nets, "count": len(nets)}
    except Exception as e:
        return exception_response(e)


@router.get("/networks/{container_id}/info")
async def api_network_info(container_id: str):
    """Get network details for a specific container."""
    try:
        info = get_network_info_via_mcp(container_id)
        return {"container_id": container_id, "networks": info}
    except Exception as e:
        return exception_response(e)


@router.post("/networks/cleanup")
async def api_cleanup_networks():
    """Remove empty isolated TRION networks."""
    try:
        removed = cleanup_networks_via_mcp()
        return {"removed": removed, "count": len(removed)}
    except Exception as e:
        return exception_response(e)


@router.get("/storage/scopes")
async def api_list_storage_scopes():
    """List all approved storage scopes."""
    try:
        from commander_storage_scope_store import list_scopes

        scopes = list_scopes()
        return {"scopes": scopes, "count": len(scopes)}
    except Exception as e:
        return exception_response(e)


@router.get("/storage/managed-paths")
async def api_list_storage_managed_paths():
    """
    List Storage-Broker managed paths as a UI-friendly catalog for deploy pickers.
    This slice is intentionally owned by the storage-broker contract, not by
    legacy Commander scope or asset registries.
    """
    try:
        from storage_broker_routes import _mcp_call  # lazy import: optional service

        payload = await _mcp_call("storage_list_managed_paths")
        raw_paths = payload.get("managed_paths", []) if isinstance(payload, dict) else []
        normalized = _managed_path_catalog(raw_paths if isinstance(raw_paths, list) else [])
        return {"managed_paths": [item["path"] for item in normalized], "catalog": normalized, "count": len(normalized)}
    except Exception as e:
        return exception_response(e)


@router.get("/storage/assets")
async def api_list_storage_assets(published_only: bool = False):
    """List shared storage assets published by Storage Manager for Commander use."""
    try:
        from commander_storage_assets_store import list_assets

        assets = list_assets(published_only=published_only)
        return {"assets": assets, "count": len(assets)}
    except Exception as e:
        return exception_response(e)


@router.get("/storage/assets/{asset_id}")
async def api_get_storage_asset(asset_id: str):
    """Get one shared storage asset."""
    try:
        from commander_storage_assets_store import get_asset

        asset = get_asset(asset_id)
        if not asset:
            return exception_response(
                HTTPException(404, f"Storage asset '{asset_id}' not found"),
                error_code="not_found",
                details={"asset_id": asset_id},
            )
        return {"asset": asset}
    except Exception as e:
        return exception_response(e)


@router.post("/storage/assets")
async def api_upsert_storage_asset(request: Request):
    """Create or update a shared storage asset entry."""
    try:
        from commander_storage_assets_store import upsert_asset

        data = await request.json()
        asset_id = str(data.get("id", "")).strip()
        asset = upsert_asset(asset_id, data)
        return {"stored": True, "asset": asset}
    except Exception as e:
        return exception_response(e)


@router.delete("/storage/assets/{asset_id}")
async def api_delete_storage_asset(asset_id: str):
    """Delete one shared storage asset entry."""
    try:
        from commander_storage_assets_store import delete_asset

        deleted = delete_asset(asset_id)
        if not deleted:
            return exception_response(
                HTTPException(404, f"Storage asset '{asset_id}' not found"),
                error_code="not_found",
                details={"asset_id": asset_id, "deleted": False},
            )
        return {"deleted": True, "asset_id": asset_id}
    except Exception as e:
        return exception_response(e)


@router.get("/storage/scopes/{scope_name}")
async def api_get_storage_scope(scope_name: str):
    """Get one storage scope."""
    try:
        from commander_storage_scope_store import get_scope

        scope = get_scope(scope_name)
        if not scope:
            return exception_response(
                HTTPException(404, f"Storage scope '{scope_name}' not found"),
                error_code="not_found",
                details={"scope_name": scope_name},
            )
        return {"scope": scope}
    except Exception as e:
        return exception_response(e)


@router.post("/storage/scopes")
async def api_upsert_storage_scope(request: Request):
    """Create or update an approved storage scope."""
    try:
        from commander_storage_scope_store import upsert_scope

        data = await request.json()
        name = str(data.get("name", "")).strip()
        roots = data.get("roots", [])
        approved_by = str(data.get("approved_by", "user")).strip() or "user"
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else None
        scope = upsert_scope(name=name, roots=roots, approved_by=approved_by, metadata=metadata)
        return {"stored": True, "scope": scope}
    except Exception as e:
        return exception_response(e)


@router.delete("/storage/scopes/{scope_name}")
async def api_delete_storage_scope(scope_name: str):
    """Delete a storage scope."""
    try:
        from commander_storage_scope_store import delete_scope

        deleted = delete_scope(scope_name)
        if not deleted:
            return exception_response(
                HTTPException(404, f"Storage scope '{scope_name}' not found"),
                error_code="not_found",
                details={"scope_name": scope_name, "deleted": False},
            )
        return {"deleted": True, "scope_name": scope_name}
    except Exception as e:
        return exception_response(e)
