from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException


RuntimeCall = Callable[..., dict[str, Any]]


def list_networks_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> list[dict[str, Any]]:
    result = call_runtime_tool("network_list", {}, timeout=timeout)
    networks = result.get("networks")
    return list(networks) if isinstance(networks, list) else []


def get_network_info_via_mcp(call_runtime_tool: RuntimeCall, container_id: str, *, timeout: float) -> dict[str, Any]:
    result = call_runtime_tool("network_info", {"container_id": container_id}, timeout=timeout)
    networks = result.get("networks")
    if not isinstance(networks, dict):
        raise HTTPException(status_code=502, detail="invalid_network_info_result")
    return networks


def cleanup_networks_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> list[str]:
    result = call_runtime_tool("network_cleanup", {}, timeout=timeout)
    removed = result.get("removed")
    return list(removed) if isinstance(removed, list) else []


def start_proxy_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> bool:
    return bool(call_runtime_tool("proxy_start", {}, timeout=timeout).get("started"))


def stop_proxy_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> bool:
    return bool(call_runtime_tool("proxy_stop", {}, timeout=timeout).get("stopped"))


def get_proxy_whitelist_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> list[str]:
    result = call_runtime_tool("proxy_whitelist_get", {"blueprint_id": blueprint_id}, timeout=timeout)
    domains = result.get("domains")
    return list(domains) if isinstance(domains, list) else []


def set_proxy_whitelist_via_mcp(
    call_runtime_tool: RuntimeCall,
    blueprint_id: str,
    domains: list[str],
    *,
    timeout: float,
) -> bool:
    result = call_runtime_tool(
        "proxy_whitelist_set",
        {"blueprint_id": blueprint_id, "domains": list(domains)},
        timeout=timeout,
    )
    return bool(result.get("updated"))


def get_dashboard_overview_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("dashboard_overview", {}, timeout=timeout)


def check_host_companion_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("host_companion_check", {"blueprint_id": blueprint_id}, timeout=timeout)


def repair_host_companion_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("host_companion_repair", {"blueprint_id": blueprint_id}, timeout=timeout)


def uninstall_host_companion_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("host_companion_uninstall", {"blueprint_id": blueprint_id}, timeout=timeout)


def get_package_manifest_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> dict[str, Any]:
    result = call_runtime_tool("package_manifest_get", {"blueprint_id": blueprint_id}, timeout=timeout)
    manifest = result.get("manifest")
    return manifest if isinstance(manifest, dict) else {}
