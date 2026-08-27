#!/usr/bin/env python3

from host_companion_views import check_host_companion, repair_host_companion, uninstall_host_companion, get_package_manifest

def host_companion_check(blueprint_id: str) -> dict:
    """Inspect host-companion/package manifest status for one blueprint."""
    return check_host_companion(blueprint_id)

def host_companion_repair(blueprint_id: str) -> dict:
    """Attempt host-companion repair for one blueprint."""
    return repair_host_companion(blueprint_id)

def host_companion_uninstall(blueprint_id: str) -> dict:
    """Attempt host-companion uninstall for one blueprint."""
    return uninstall_host_companion(blueprint_id)

def package_manifest_get(blueprint_id: str) -> dict:
    """Read the local package manifest for one blueprint if present."""
    return get_package_manifest(blueprint_id)
