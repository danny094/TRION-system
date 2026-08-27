#!/usr/bin/env python3

from bundle_network import list_networks, get_network_info, cleanup_networks
from proxy_views import ensure_proxy_running, stop_proxy, get_whitelist, set_whitelist

def network_list() -> dict:
    """List TRION-managed Docker networks."""
    return list_networks()

def network_info(container_id: str = "", container_name: str = "") -> dict:
    """Get network details for a specific container."""
    return get_network_info(container_id=container_id, container_name=container_name)

def network_cleanup() -> dict:
    """Remove empty isolated TRION-managed networks."""
    return cleanup_networks()

def proxy_start() -> dict:
    """Enable the commander proxy policy surface."""
    return ensure_proxy_running()

def proxy_stop() -> dict:
    """Disable the commander proxy policy surface."""
    return stop_proxy()

def proxy_whitelist_get(blueprint_id: str) -> dict:
    """Read the allowed outbound domains for one blueprint."""
    return get_whitelist(blueprint_id)

def proxy_whitelist_set(blueprint_id: str, domains: list[str]) -> dict:
    """Store the allowed outbound domains for one blueprint."""
    return set_whitelist(blueprint_id, domains)
