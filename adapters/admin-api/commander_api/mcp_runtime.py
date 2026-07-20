from __future__ import annotations

from typing import Any
import base64

from fastapi import HTTPException

from mcp.client import call_tool


_DEFAULT_TIMEOUT_S = 5.0

_ERROR_STATUS = {
    "CONTAINER_NOT_FOUND": 404,
    "VOLUME_NOT_FOUND": 404,
    "ACTION_NOT_ALLOWED": 409,
    "RUNTIME_UNAVAILABLE": 503,
}


def _unwrap_tool_result(tool_name: str, payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and payload.get("error") and "result" not in payload:
        raise HTTPException(status_code=503, detail=str(payload.get("error")))
    result = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    if result.get("ok") is False and isinstance(result.get("error"), dict):
        error = result.get("error") or {}
        code = str(error.get("code") or "").strip() or "commander_error"
        message = str(error.get("message") or code).strip() or code
        raise HTTPException(status_code=_ERROR_STATUS.get(code, 502), detail=message)
    return result


def call_commander_runtime_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    payload = call_tool(tool_name, arguments or {}, timeout=timeout)
    if payload is None:
        raise HTTPException(status_code=503, detail=f"{tool_name}_unavailable")
    return _unwrap_tool_result(tool_name, payload)


def list_containers_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    result = call_commander_runtime_tool("container_list", {}, timeout=timeout)
    containers = result.get("containers")
    return list(containers) if isinstance(containers, list) else []


def inspect_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    result = call_commander_runtime_tool(
        "container_inspect",
        {"container_id": container_id},
        timeout=timeout,
    )
    container = result.get("container")
    if not isinstance(container, dict):
        raise HTTPException(status_code=502, detail="invalid_container_inspect_result")
    return container


def get_container_logs_via_mcp(
    container_id: str,
    *,
    tail: int = 100,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "container_logs",
        {"container_id": container_id, "tail": int(tail)},
        timeout=timeout,
    )


def get_container_stats_via_mcp(
    container_id: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "container_stats",
        {"container_id": container_id},
        timeout=timeout,
    )


def get_runtime_quota_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool("runtime_quota", {}, timeout=timeout)


def exec_in_container_via_mcp(
    container_id: str,
    command: str,
    *,
    timeout: int = 30,
    rpc_timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "container_exec",
        {"container_id": container_id, "command": command, "timeout": int(timeout)},
        timeout=rpc_timeout,
    )


def exec_in_container_detailed_via_mcp(
    container_id: str,
    command: str,
    *,
    timeout: int = 30,
    rpc_timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "container_exec_detailed",
        {"container_id": container_id, "command": command, "timeout": int(timeout)},
        timeout=rpc_timeout,
    )


def cleanup_all_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool("runtime_cleanup_all", {}, timeout=timeout)


def remove_stopped_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "remove_stopped_container",
        {"container_id": container_id},
        timeout=timeout,
    )


def list_networks_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    result = call_commander_runtime_tool("network_list", {}, timeout=timeout)
    networks = result.get("networks")
    return list(networks) if isinstance(networks, list) else []


def get_network_info_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    result = call_commander_runtime_tool(
        "network_info",
        {"container_id": container_id},
        timeout=timeout,
    )
    networks = result.get("networks")
    if not isinstance(networks, dict):
        raise HTTPException(status_code=502, detail="invalid_network_info_result")
    return networks


def cleanup_networks_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[str]:
    result = call_commander_runtime_tool("network_cleanup", {}, timeout=timeout)
    removed = result.get("removed")
    return list(removed) if isinstance(removed, list) else []


def start_proxy_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    result = call_commander_runtime_tool("proxy_start", {}, timeout=timeout)
    return bool(result.get("started"))


def stop_proxy_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    result = call_commander_runtime_tool("proxy_stop", {}, timeout=timeout)
    return bool(result.get("stopped"))


def get_proxy_whitelist_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> list[str]:
    result = call_commander_runtime_tool(
        "proxy_whitelist_get",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )
    domains = result.get("domains")
    return list(domains) if isinstance(domains, list) else []


def set_proxy_whitelist_via_mcp(
    blueprint_id: str,
    domains: list[str],
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> bool:
    result = call_commander_runtime_tool(
        "proxy_whitelist_set",
        {"blueprint_id": blueprint_id, "domains": list(domains)},
        timeout=timeout,
    )
    return bool(result.get("updated"))


def get_dashboard_overview_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool("dashboard_overview", {}, timeout=timeout)


def check_host_companion_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "host_companion_check",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )


def repair_host_companion_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "host_companion_repair",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )


def uninstall_host_companion_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "host_companion_uninstall",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )


def get_package_manifest_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    result = call_commander_runtime_tool(
        "package_manifest_get",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )
    manifest = result.get("manifest")
    return manifest if isinstance(manifest, dict) else {}


def list_marketplace_bundles_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool("marketplace_bundle_list", {}, timeout=timeout)


def list_marketplace_starters_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool("marketplace_starter_list", {}, timeout=timeout)


def list_marketplace_catalog_via_mcp(
    *,
    category: str = "",
    trusted_only: bool = False,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "marketplace_catalog_list",
        {"category": category, "trusted_only": bool(trusted_only)},
        timeout=timeout,
    )


def sync_marketplace_catalog_via_mcp(
    *,
    repo_url: str = "",
    branch: str = "main",
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "marketplace_catalog_sync",
        {"repo_url": repo_url, "branch": branch},
        timeout=timeout,
    )


def install_marketplace_starter_via_mcp(starter_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "marketplace_starter_install",
        {"starter_id": starter_id},
        timeout=timeout,
    )


def install_marketplace_catalog_blueprint_via_mcp(
    blueprint_id: str,
    *,
    overwrite: bool = False,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "marketplace_catalog_install",
        {"blueprint_id": blueprint_id, "overwrite": bool(overwrite)},
        timeout=timeout,
    )


def export_marketplace_bundle_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "marketplace_bundle_export",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )


def import_marketplace_bundle_via_mcp(
    bundle_bytes: bytes,
    *,
    filename: str = "",
    overwrite: bool = False,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "marketplace_bundle_import",
        {
            "bundle_bytes_b64": base64.b64encode(bundle_bytes).decode("utf-8"),
            "filename": filename,
            "overwrite": bool(overwrite),
        },
        timeout=timeout,
    )


def list_volumes_via_mcp(blueprint_id: str = "", *, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    result = call_commander_runtime_tool(
        "volume_list",
        {"blueprint_id": blueprint_id} if blueprint_id else {},
        timeout=timeout,
    )
    volumes = result.get("volumes")
    return list(volumes) if isinstance(volumes, list) else []


def get_volume_via_mcp(volume_name: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    result = call_commander_runtime_tool(
        "volume_get",
        {"volume_name": volume_name},
        timeout=timeout,
    )
    volume = result.get("volume")
    if not isinstance(volume, dict):
        raise HTTPException(status_code=502, detail="invalid_volume_get_result")
    return volume


def remove_volume_via_mcp(volume_name: str, *, force: bool = False, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    result = call_commander_runtime_tool(
        "volume_remove",
        {"volume_name": volume_name, "force": bool(force)},
        timeout=timeout,
    )
    return bool(result.get("removed"))


def cleanup_orphaned_volumes_via_mcp(*, dry_run: bool = True, timeout: float = _DEFAULT_TIMEOUT_S) -> list[str]:
    result = call_commander_runtime_tool(
        "volume_cleanup",
        {"dry_run": bool(dry_run)},
        timeout=timeout,
    )
    orphaned = result.get("orphaned")
    return list(orphaned) if isinstance(orphaned, list) else []


def list_snapshots_via_mcp(volume_name: str = "", *, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    result = call_commander_runtime_tool(
        "snapshot_list",
        {"volume_name": volume_name} if volume_name else {},
        timeout=timeout,
    )
    snapshots = result.get("snapshots")
    return list(snapshots) if isinstance(snapshots, list) else []


def delete_snapshot_via_mcp(filename: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    result = call_commander_runtime_tool(
        "snapshot_delete",
        {"filename": filename},
        timeout=timeout,
    )
    return bool(result.get("deleted"))


def create_snapshot_via_mcp(volume_name: str, *, tag: str = "", timeout: float = _DEFAULT_TIMEOUT_S) -> str:
    result = call_commander_runtime_tool(
        "snapshot_create",
        {"volume_name": volume_name, "tag": tag},
        timeout=timeout,
    )
    if not bool(result.get("created")):
        return ""
    filename = result.get("filename")
    return str(filename) if isinstance(filename, str) else ""


def restore_snapshot_via_mcp(filename: str, *, target_volume: str = "", timeout: float = _DEFAULT_TIMEOUT_S) -> str:
    result = call_commander_runtime_tool(
        "snapshot_restore",
        {"filename": filename, "target_volume": target_volume},
        timeout=timeout,
    )
    if not bool(result.get("restored")):
        return ""
    volume = result.get("volume")
    return str(volume) if isinstance(volume, str) else ""


def start_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "start_stopped_container",
        {"container_id": container_id},
        timeout=timeout,
    )


def stop_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_runtime_tool(
        "stop_container",
        {"container_id": container_id},
        timeout=timeout,
    )


def evaluate_home_status_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    containers = list_containers_via_mcp(timeout=timeout)
    if not containers:
        return {"status": "offline", "error_code": "home_not_found"}

    candidates = sorted(
        containers,
        key=lambda item: 0 if str(item.get("name") or "").strip() == "trion-home" else 1,
    )
    for item in candidates:
        container_id = str(item.get("container_id") or "").strip()
        if not container_id:
            continue
        try:
            details = inspect_container_via_mcp(container_id, timeout=timeout)
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
