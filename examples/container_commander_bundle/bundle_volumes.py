#!/usr/bin/env python3
import bundle_docker
from bundle_common import TRION_LABEL, error_result, is_not_found
from bundle_snapshots import list_snapshots


def list_volumes(blueprint_id=""):
    try:
        client = bundle_docker.get_docker_client()
        result = []
        for volume in client.volumes.list(filters={"label": TRION_LABEL}):
            labels = dict((volume.attrs or {}).get("Labels") or {})
            bp = str(labels.get("trion.blueprint") or "")
            if blueprint_id and bp != blueprint_id:
                continue
            result.append(
                {
                    "name": volume.name,
                    "blueprint_id": bp,
                    "created_at": str(labels.get("trion.created") or (volume.attrs or {}).get("CreatedAt") or ""),
                    "driver": str((volume.attrs or {}).get("Driver") or "local"),
                    "mountpoint": str((volume.attrs or {}).get("Mountpoint") or ""),
                }
            )
        result.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {"volumes": result}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def get_volume(volume_name):
    try:
        client = bundle_docker.get_docker_client()
        volume = client.volumes.get(volume_name)
        labels = dict((volume.attrs or {}).get("Labels") or {})
        return {
            "volume": {
                "name": volume.name,
                "blueprint_id": str(labels.get("trion.blueprint") or ""),
                "created_at": str(labels.get("trion.created") or (volume.attrs or {}).get("CreatedAt") or ""),
                "driver": str((volume.attrs or {}).get("Driver") or "local"),
                "mountpoint": str((volume.attrs or {}).get("Mountpoint") or ""),
                "snapshots": list_snapshots(volume_name).get("snapshots", []),
            }
        }
    except Exception as exc:
        if is_not_found(exc):
            return error_result("VOLUME_NOT_FOUND", f"Volume '{volume_name}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def remove_volume(volume_name, force=False):
    try:
        client = bundle_docker.get_docker_client()
        volume = client.volumes.get(volume_name)
        volume.remove(force=bool(force))
        return {"removed": True, "volume": volume_name}
    except Exception as exc:
        if is_not_found(exc):
            return {"removed": False, "volume": volume_name}
        if "volume is in use" in str(exc).lower():
            return {"removed": False, "volume": volume_name}
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def cleanup_orphaned_volumes(dry_run=True):
    try:
        client = bundle_docker.get_docker_client()
        active_volumes = set()
        for container in client.containers.list(all=True):
            for mount in (container.attrs or {}).get("Mounts", []):
                name = str((mount or {}).get("Name") or "").strip()
                if name:
                    active_volumes.add(name)

        orphaned = []
        for volume in client.volumes.list(filters={"label": TRION_LABEL}):
            if volume.name in active_volumes:
                continue
            orphaned.append(volume.name)
            if not dry_run:
                volume.remove()
        return {"orphaned": orphaned, "dry_run": bool(dry_run)}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)
