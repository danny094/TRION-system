"""
Shared network compatibility helpers.

This module is the local truth for the remaining legacy `container_commander.network`
public wrapper surface.
"""

from __future__ import annotations

from commander_network_runtime import (
    APIError,
    NotFound,
    TRION_LABEL,
    cleanup_networks_via_mcp,
    create_isolated_network,
    get_network_info_via_mcp,
    get_runtime_client,
    list_networks_via_mcp,
    logger,
)
from commander_deploy_container_run import ensure_shared_network as ensure_shared_network_local
from commander_deploy_container_run import resolve_network as resolve_network_local


def ensure_shared_network() -> str:
    return ensure_shared_network_local()


def resolve_network(mode, container_name: str = ""):
    return resolve_network_local(mode, container_name)


def list_networks():
    return list_networks_via_mcp()


def remove_network(network_name: str) -> bool:
    client = get_runtime_client()
    try:
        net = client.networks.get(network_name)
        labels = dict((net.attrs or {}).get("Labels") or {})
        if str(labels.get(TRION_LABEL) or "").strip().lower() != "true":
            logger.warning("[Network] Refusing to remove non-TRION network: %s", network_name)
            return False
        net.remove()
        logger.info("[Network] Removed: %s", network_name)
        return True
    except NotFound:
        return False
    except APIError as exc:
        if "has active endpoints" in str(exc).lower():
            logger.warning("[Network] Cannot remove %s: containers still connected", network_name)
        else:
            logger.error("[Network] Remove failed: %s", exc)
        return False


def cleanup_networks():
    return cleanup_networks_via_mcp()


def get_network_info(container_id: str):
    return get_network_info_via_mcp(container_id)
