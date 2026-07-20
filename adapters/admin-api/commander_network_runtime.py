"""
Commander network runtime helpers.

Local truth for the remaining isolated-network create/remove helpers plus
MCP-backed network read accessors.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from commander_api.mcp_runtime import (
    cleanup_networks_via_mcp,
    get_network_info_via_mcp,
    list_networks_via_mcp,
)
from commander_deploy_container_run import ensure_shared_network, resolve_network
from commander_deploy_runtime_client import TRION_LABEL, get_runtime_client

try:
    from docker.errors import APIError, NotFound
except Exception:  # pragma: no cover - lightweight import-only test envs
    class APIError(Exception):
        pass

    class NotFound(Exception):
        pass


logger = logging.getLogger(__name__)


def create_isolated_network(container_name: str) -> str:
    client = get_runtime_client()
    net_name = f"trion-iso-{container_name}"
    try:
        client.networks.create(
            net_name,
            driver="bridge",
            internal=True,
            labels={
                TRION_LABEL: "true",
                "trion.network.type": "isolated",
                "trion.network.container": container_name,
            },
        )
    except APIError as exc:
        if "already exists" in str(exc).lower():
            logger.debug("[Network] %s already exists", net_name)
        else:
            raise
    return net_name


def list_networks() -> List[Dict[str, Any]]:
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


def cleanup_networks() -> List[str]:
    return cleanup_networks_via_mcp()


def get_network_info(container_id: str) -> Optional[Dict[str, Any]]:
    return get_network_info_via_mcp(container_id)
