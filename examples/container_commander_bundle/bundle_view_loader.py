#!/usr/bin/env python3
import importlib.util
from pathlib import Path


def _load_local_module(name: str, filename: str):
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"container_commander_bundle_{name}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed_to_load_{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_proxy_views = _load_local_module("proxy_views", "proxy_views.py")
ensure_proxy_running = _proxy_views.ensure_proxy_running
get_whitelist = _proxy_views.get_whitelist
set_whitelist = _proxy_views.set_whitelist
stop_proxy = _proxy_views.stop_proxy

_dashboard_views = _load_local_module("dashboard_views", "dashboard_views.py")
get_dashboard_overview = _dashboard_views.get_dashboard_overview
_host_companion_views = _load_local_module("host_companion_views", "host_companion_views.py")
check_host_companion = _host_companion_views.check_host_companion
repair_host_companion = _host_companion_views.repair_host_companion
uninstall_host_companion = _host_companion_views.uninstall_host_companion
get_package_manifest = _host_companion_views.get_package_manifest
_marketplace_views = _load_local_module("marketplace_views", "marketplace_views.py")
get_starters = _marketplace_views.get_starters
list_bundles = _marketplace_views.list_bundles
list_catalog = _marketplace_views.list_catalog
sync_remote_catalog = _marketplace_views.sync_remote_catalog
_marketplace_mutations = _load_local_module("marketplace_mutations", "marketplace_mutations.py")
install_starter = _marketplace_mutations.install_starter
install_catalog_blueprint = _marketplace_mutations.install_catalog_blueprint
export_bundle = _marketplace_mutations.export_bundle
import_bundle = _marketplace_mutations.import_bundle
