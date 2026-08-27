#!/usr/bin/env python3
from bundle_view_loader import (
    _marketplace_mutations,
    _marketplace_views,
    check_host_companion,
    ensure_proxy_running,
    export_bundle,
    get_dashboard_overview,
    get_package_manifest,
    get_starters,
    get_whitelist,
    import_bundle,
    install_catalog_blueprint,
    install_starter,
    list_bundles,
    list_catalog,
    repair_host_companion,
    set_whitelist,
    stop_proxy,
    sync_remote_catalog,
    uninstall_host_companion,
)

from bundle_common import HOME_ROOT, MANIFEST_PATH, TRION_LABEL, SNAPSHOT_DIR, DEFAULT_WRITE_ROOTS, HOME_CAPABILITY_CLASSES, AVAILABLE_HOME_CAPABILITIES, error_result, is_not_found, is_true, managed_flags, created_at, port_rows, _db_path, container_summary, resolve_container_reference, action_result, guard_managed_action
from bundle_home import is_home_container, blueprint_id_from_labels, parse_home_manifest, read_home_manifest, build_home_scope
from bundle_runtime_views import list_containers, inspect_container, get_container_logs, get_container_stats, runtime_quota
from bundle_runtime_actions import runtime_cleanup_all, remove_stopped_container, start_stopped_container, stop_container
from bundle_exec import MAX_EXEC_OUTPUT, EXEC_TIMEOUT_EXIT_CODE, EXEC_TIMEOUT_MARKER, _allowed_exec, _check_exec_policy, _build_timed_exec_command, _extract_timeout_marker, _exec_run_with_workdir_fallback, container_exec, container_exec_detailed
from bundle_network import list_networks, get_network_info, _remove_network, cleanup_networks
from bundle_volumes import list_volumes, get_volume, remove_volume, cleanup_orphaned_volumes
from bundle_snapshots import list_snapshots, delete_snapshot, create_snapshot, restore_snapshot
from bundle_blueprint_store import get_conn, ensure_store_initialized, load_json, row_value, row_version, blueprint_definition, list_blueprints, get_blueprint
from bundle_yaml import yaml, json_text, parse_simple_yaml, yaml_load, yaml_dump
from bundle_blueprint_write import normalize_blueprint, blueprint_trust, create_blueprint, update_blueprint, delete_blueprint, import_blueprint_yaml, export_blueprint_yaml
from bundle_docker import get_docker_client
from bundle_dispatch import TOOLS, handle_request
from bundle_stdio import run_stdio_loop

main = run_stdio_loop

if __name__ == "__main__":
    main()
