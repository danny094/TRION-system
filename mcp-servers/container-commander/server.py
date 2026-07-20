"""
Container Commander v2 — MCP Server Entry Point

Phase 1 only exposes read-only tools with a stable contract.
"""

from fastmcp import FastMCP

from blueprint_store import get_blueprint, list_blueprints
from blueprint_write import create_blueprint, delete_blueprint, export_blueprint_yaml, import_blueprint_yaml, update_blueprint
from dashboard_views import get_dashboard_overview
from exec_views import exec_in_container, exec_in_container_detailed
from host_companion_views import check_host_companion, get_package_manifest, repair_host_companion, uninstall_host_companion
from marketplace_mutations import export_bundle, import_bundle, install_catalog_blueprint, install_starter
from marketplace_views import get_starters, list_bundles, list_catalog, sync_remote_catalog
from network_views import cleanup_networks, get_network_info, list_networks
from proxy_views import ensure_proxy_running, get_whitelist, set_whitelist, stop_proxy
from runtime_views import (
    cleanup_all as runtime_cleanup_all_view,
    get_container_logs,
    get_runtime_quota,
    get_container_stats,
    inspect_container,
    list_containers,
    remove_stopped_container as runtime_remove_stopped_container,
    start_stopped_container as runtime_start_stopped_container,
    stop_container as runtime_stop_container,
)
from volume_views import cleanup_orphaned_volumes, create_snapshot, delete_snapshot, get_volume, list_snapshots, list_volumes, remove_volume, restore_snapshot

mcp = FastMCP("container-commander")


@mcp.tool
def container_list() -> dict:
    """List containers with stable v2 summary fields."""
    return list_containers()


@mcp.tool
def container_inspect(container_id: str) -> dict:
    """Inspect one container with stable v2 detail fields."""
    return inspect_container(container_id)


@mcp.tool
def container_logs(container_id: str, tail: int = 200, since: str = "", limit_chars: int = 16000) -> dict:
    """Read bounded container logs."""
    return get_container_logs(container_id, tail=tail, since=since, limit_chars=limit_chars)


@mcp.tool
def container_stats(container_id: str) -> dict:
    """Read live container resource stats with a stable v2 shape."""
    return get_container_stats(container_id)


@mcp.tool
def runtime_quota() -> dict:
    """Read runtime session quota limits and current managed usage."""
    return get_runtime_quota()


@mcp.tool
def container_exec(container_id: str, command: str, timeout: int = 30) -> dict:
    """Execute one bounded command inside a running container."""
    return exec_in_container(container_id, command, timeout=timeout)


@mcp.tool
def container_exec_detailed(container_id: str, command: str, timeout: int = 30) -> dict:
    """Execute one bounded command and return split stdout/stderr details."""
    return exec_in_container_detailed(container_id, command, timeout=timeout)


@mcp.tool
def runtime_cleanup_all() -> dict:
    """Stop and remove all TRION-managed containers."""
    return runtime_cleanup_all_view()


@mcp.tool
def remove_stopped_container(container_id: str) -> dict:
    """Remove one stopped TRION-managed container."""
    return runtime_remove_stopped_container(container_id)


@mcp.tool
def blueprint_list() -> dict:
    """List blueprints with the v2 summary shape."""
    return list_blueprints()


@mcp.tool
def blueprint_get(blueprint_id: str) -> dict:
    """Get one blueprint with the v2 detail shape."""
    return get_blueprint(blueprint_id)


@mcp.tool
def blueprint_create(blueprint: dict) -> dict:
    """Create one blueprint in the commander store."""
    return create_blueprint(blueprint)


@mcp.tool
def blueprint_update(blueprint_id: str, updates: dict) -> dict:
    """Update one blueprint in the commander store."""
    return update_blueprint(blueprint_id, updates)


@mcp.tool
def blueprint_delete(blueprint_id: str) -> dict:
    """Soft-delete one blueprint in the commander store."""
    return delete_blueprint(blueprint_id)


@mcp.tool
def blueprint_import_yaml(yaml: str) -> dict:
    """Import one blueprint from YAML."""
    return import_blueprint_yaml(yaml)


@mcp.tool
def blueprint_export_yaml(blueprint_id: str) -> dict:
    """Export one blueprint as YAML."""
    return export_blueprint_yaml(blueprint_id)


@mcp.tool
def network_list() -> dict:
    """List TRION-managed Docker networks."""
    return list_networks()


@mcp.tool
def network_info(container_id: str) -> dict:
    """Get network details for a specific container."""
    return get_network_info(container_id)


@mcp.tool
def network_cleanup() -> dict:
    """Remove empty isolated TRION-managed networks."""
    return cleanup_networks()


@mcp.tool
def proxy_start() -> dict:
    """Enable the commander proxy policy surface."""
    return ensure_proxy_running()


@mcp.tool
def proxy_stop() -> dict:
    """Disable the commander proxy policy surface."""
    return stop_proxy()


@mcp.tool
def proxy_whitelist_get(blueprint_id: str) -> dict:
    """Read the allowed outbound domains for one blueprint."""
    return get_whitelist(blueprint_id)


@mcp.tool
def proxy_whitelist_set(blueprint_id: str, domains: list[str]) -> dict:
    """Store the allowed outbound domains for one blueprint."""
    return set_whitelist(blueprint_id, domains)


@mcp.tool
def dashboard_overview() -> dict:
    """Aggregate commander runtime inventory into a dashboard-shaped read model."""
    return get_dashboard_overview()


@mcp.tool
def host_companion_check(blueprint_id: str) -> dict:
    """Inspect host-companion/package manifest status for one blueprint."""
    return check_host_companion(blueprint_id)


@mcp.tool
def host_companion_repair(blueprint_id: str) -> dict:
    """Attempt host-companion repair for one blueprint."""
    return repair_host_companion(blueprint_id)


@mcp.tool
def host_companion_uninstall(blueprint_id: str) -> dict:
    """Attempt host-companion uninstall for one blueprint."""
    return uninstall_host_companion(blueprint_id)


@mcp.tool
def package_manifest_get(blueprint_id: str) -> dict:
    """Read the local package manifest for one blueprint if present."""
    return get_package_manifest(blueprint_id)


@mcp.tool
def marketplace_bundle_list() -> dict:
    """List exported marketplace bundles from the commander marketplace directory."""
    bundles = list_bundles()
    return {"bundles": bundles, "count": len(bundles)}


@mcp.tool
def marketplace_starter_list() -> dict:
    """List built-in starter blueprints."""
    starters = get_starters()
    return {"starters": starters, "count": len(starters)}


@mcp.tool
def marketplace_catalog_list(category: str = "", trusted_only: bool = False) -> dict:
    """List cached catalog entries, optionally filtered by category and trust."""
    return list_catalog(category=category, trusted_only=trusted_only)


@mcp.tool
def marketplace_catalog_sync(repo_url: str = "", branch: str = "main") -> dict:
    """Refresh the remote blueprint catalog cache from a GitHub-backed index."""
    return sync_remote_catalog(repo_url=repo_url, branch=branch)


@mcp.tool
def marketplace_starter_install(starter_id: str) -> dict:
    """Install one built-in starter blueprint into the commander store."""
    return install_starter(starter_id)


@mcp.tool
def marketplace_catalog_install(blueprint_id: str, overwrite: bool = False) -> dict:
    """Install one blueprint from the cached remote catalog."""
    return install_catalog_blueprint(blueprint_id=blueprint_id, overwrite=overwrite)


@mcp.tool
def marketplace_bundle_export(blueprint_id: str) -> dict:
    """Export one blueprint as a shareable TRION bundle."""
    filename = export_bundle(blueprint_id)
    if not filename:
        return {"exported": False, "blueprint_id": blueprint_id}
    return {"exported": True, "filename": filename}


@mcp.tool
def marketplace_bundle_import(bundle_bytes_b64: str, filename: str = "", overwrite: bool = False) -> dict:
    """Import one TRION bundle from base64-encoded archive bytes."""
    import base64

    bundle_bytes = base64.b64decode(bundle_bytes_b64.encode("utf-8"))
    result = import_bundle(bundle_bytes, filename=filename, overwrite=overwrite)
    return result if isinstance(result, dict) else {"error": "import_failed"}


@mcp.tool
def volume_list(blueprint_id: str = "") -> dict:
    """List TRION-managed workspace volumes."""
    return list_volumes(blueprint_id)


@mcp.tool
def volume_get(volume_name: str) -> dict:
    """Get one volume with snapshot metadata."""
    return get_volume(volume_name)


@mcp.tool
def volume_remove(volume_name: str, force: bool = False) -> dict:
    """Remove one workspace volume."""
    return remove_volume(volume_name, force=force)


@mcp.tool
def volume_cleanup(dry_run: bool = True) -> dict:
    """Find and optionally remove orphaned workspace volumes."""
    return cleanup_orphaned_volumes(dry_run=dry_run)


@mcp.tool
def snapshot_list(volume_name: str = "") -> dict:
    """List snapshots, optionally filtered by volume prefix."""
    return list_snapshots(volume_name)


@mcp.tool
def snapshot_delete(filename: str) -> dict:
    """Delete one stored snapshot tarball."""
    return delete_snapshot(filename)


@mcp.tool
def snapshot_create(volume_name: str, tag: str = "") -> dict:
    """Create one snapshot tarball for a workspace volume."""
    return create_snapshot(volume_name, tag=tag)


@mcp.tool
def snapshot_restore(filename: str, target_volume: str = "") -> dict:
    """Restore one snapshot tarball into a target or derived volume."""
    return restore_snapshot(filename, target_volume=target_volume)


@mcp.tool
def start_stopped_container(container_id: str) -> dict:
    """Start a stopped TRION-managed container."""
    return runtime_start_stopped_container(container_id)


@mcp.tool
def stop_container(container_id: str) -> dict:
    """Stop a running TRION-managed container."""
    return runtime_stop_container(container_id)


if __name__ == "__main__":
    mcp.run()
