from __future__ import annotations

from typing import Any

from commander_api import mcp_runtime_container as _container
from commander_api import mcp_runtime_marketplace as _marketplace
from commander_api import mcp_runtime_platform as _platform
from commander_api import mcp_runtime_storage as _storage
from commander_api import mcp_runtime_handoff as _handoff
from mcp.client import call_tool


_DEFAULT_TIMEOUT_S = 5.0
_ERROR_STATUS = _handoff.ERROR_STATUS


def _unwrap_tool_result(tool_name: str, payload: Any) -> dict[str, Any]:
    return _handoff.unwrap_tool_result(tool_name, payload)


def call_commander_runtime_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return _handoff.call_commander_runtime_tool(call_tool, tool_name, arguments, timeout=timeout)


def list_containers_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    return _container.list_containers_via_mcp(call_commander_runtime_tool, timeout=timeout)


def inspect_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.inspect_container_via_mcp(call_commander_runtime_tool, container_id, timeout=timeout)


def get_container_logs_via_mcp(container_id: str, *, tail: int = 100, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.get_container_logs_via_mcp(call_commander_runtime_tool, container_id, tail=tail, timeout=timeout)


def get_container_stats_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.get_container_stats_via_mcp(call_commander_runtime_tool, container_id, timeout=timeout)


def get_runtime_quota_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.get_runtime_quota_via_mcp(call_commander_runtime_tool, timeout=timeout)


def exec_in_container_via_mcp(container_id: str, command: str, *, timeout: int = 30, rpc_timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.exec_in_container_via_mcp(call_commander_runtime_tool, container_id, command, timeout=timeout, rpc_timeout=rpc_timeout)


def exec_in_container_detailed_via_mcp(container_id: str, command: str, *, timeout: int = 30, rpc_timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.exec_in_container_detailed_via_mcp(call_commander_runtime_tool, container_id, command, timeout=timeout, rpc_timeout=rpc_timeout)


def cleanup_all_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.cleanup_all_via_mcp(call_commander_runtime_tool, timeout=timeout)


def remove_stopped_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.remove_stopped_container_via_mcp(call_commander_runtime_tool, container_id, timeout=timeout)


def start_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.start_container_via_mcp(call_commander_runtime_tool, container_id, timeout=timeout)


def stop_container_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.stop_container_via_mcp(call_commander_runtime_tool, container_id, timeout=timeout)


def evaluate_home_status_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _container.evaluate_home_status_via_mcp(list_containers_via_mcp, inspect_container_via_mcp, timeout=timeout)


def list_networks_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    return _platform.list_networks_via_mcp(call_commander_runtime_tool, timeout=timeout)


def get_network_info_via_mcp(container_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _platform.get_network_info_via_mcp(call_commander_runtime_tool, container_id, timeout=timeout)


def cleanup_networks_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[str]:
    return _platform.cleanup_networks_via_mcp(call_commander_runtime_tool, timeout=timeout)


def start_proxy_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    return _platform.start_proxy_via_mcp(call_commander_runtime_tool, timeout=timeout)


def stop_proxy_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    return _platform.stop_proxy_via_mcp(call_commander_runtime_tool, timeout=timeout)


def get_proxy_whitelist_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> list[str]:
    return _platform.get_proxy_whitelist_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def set_proxy_whitelist_via_mcp(blueprint_id: str, domains: list[str], *, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    return _platform.set_proxy_whitelist_via_mcp(call_commander_runtime_tool, blueprint_id, domains, timeout=timeout)


def get_dashboard_overview_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _platform.get_dashboard_overview_via_mcp(call_commander_runtime_tool, timeout=timeout)


def check_host_companion_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _platform.check_host_companion_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def repair_host_companion_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _platform.repair_host_companion_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def uninstall_host_companion_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _platform.uninstall_host_companion_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def get_package_manifest_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _platform.get_package_manifest_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def list_marketplace_bundles_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.list_marketplace_bundles_via_mcp(call_commander_runtime_tool, timeout=timeout)


def list_marketplace_starters_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.list_marketplace_starters_via_mcp(call_commander_runtime_tool, timeout=timeout)


def list_marketplace_catalog_via_mcp(*, category: str = "", trusted_only: bool = False, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.list_marketplace_catalog_via_mcp(call_commander_runtime_tool, category=category, trusted_only=trusted_only, timeout=timeout)


def sync_marketplace_catalog_via_mcp(*, repo_url: str = "", branch: str = "main", timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.sync_marketplace_catalog_via_mcp(call_commander_runtime_tool, repo_url=repo_url, branch=branch, timeout=timeout)


def install_marketplace_starter_via_mcp(starter_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.install_marketplace_starter_via_mcp(call_commander_runtime_tool, starter_id, timeout=timeout)


def install_marketplace_catalog_blueprint_via_mcp(blueprint_id: str, *, overwrite: bool = False, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.install_marketplace_catalog_blueprint_via_mcp(call_commander_runtime_tool, blueprint_id, overwrite=overwrite, timeout=timeout)


def export_marketplace_bundle_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.export_marketplace_bundle_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def import_marketplace_bundle_via_mcp(bundle_bytes: bytes, *, filename: str = "", overwrite: bool = False, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _marketplace.import_marketplace_bundle_via_mcp(call_commander_runtime_tool, bundle_bytes, filename=filename, overwrite=overwrite, timeout=timeout)


def list_volumes_via_mcp(blueprint_id: str = "", *, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    return _storage.list_volumes_via_mcp(call_commander_runtime_tool, blueprint_id, timeout=timeout)


def get_volume_via_mcp(volume_name: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return _storage.get_volume_via_mcp(call_commander_runtime_tool, volume_name, timeout=timeout)


def remove_volume_via_mcp(volume_name: str, *, force: bool = False, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    return _storage.remove_volume_via_mcp(call_commander_runtime_tool, volume_name, force=force, timeout=timeout)


def cleanup_orphaned_volumes_via_mcp(*, dry_run: bool = True, timeout: float = _DEFAULT_TIMEOUT_S) -> list[str]:
    return _storage.cleanup_orphaned_volumes_via_mcp(call_commander_runtime_tool, dry_run=dry_run, timeout=timeout)


def list_snapshots_via_mcp(volume_name: str = "", *, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    return _storage.list_snapshots_via_mcp(call_commander_runtime_tool, volume_name, timeout=timeout)


def delete_snapshot_via_mcp(filename: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> bool:
    return _storage.delete_snapshot_via_mcp(call_commander_runtime_tool, filename, timeout=timeout)


def create_snapshot_via_mcp(volume_name: str, *, tag: str = "", timeout: float = _DEFAULT_TIMEOUT_S) -> str:
    return _storage.create_snapshot_via_mcp(call_commander_runtime_tool, volume_name, tag=tag, timeout=timeout)


def restore_snapshot_via_mcp(filename: str, *, target_volume: str = "", timeout: float = _DEFAULT_TIMEOUT_S) -> str:
    return _storage.restore_snapshot_via_mcp(call_commander_runtime_tool, filename, target_volume=target_volume, timeout=timeout)
