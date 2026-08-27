from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any


RuntimeCall = Callable[..., dict[str, Any]]


def list_marketplace_bundles_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("marketplace_bundle_list", {}, timeout=timeout)


def list_marketplace_starters_via_mcp(call_runtime_tool: RuntimeCall, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("marketplace_starter_list", {}, timeout=timeout)


def list_marketplace_catalog_via_mcp(
    call_runtime_tool: RuntimeCall,
    *,
    category: str,
    trusted_only: bool,
    timeout: float,
) -> dict[str, Any]:
    return call_runtime_tool(
        "marketplace_catalog_list",
        {"category": category, "trusted_only": bool(trusted_only)},
        timeout=timeout,
    )


def sync_marketplace_catalog_via_mcp(
    call_runtime_tool: RuntimeCall,
    *,
    repo_url: str,
    branch: str,
    timeout: float,
) -> dict[str, Any]:
    return call_runtime_tool(
        "marketplace_catalog_sync",
        {"repo_url": repo_url, "branch": branch},
        timeout=timeout,
    )


def install_marketplace_starter_via_mcp(call_runtime_tool: RuntimeCall, starter_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("marketplace_starter_install", {"starter_id": starter_id}, timeout=timeout)


def install_marketplace_catalog_blueprint_via_mcp(
    call_runtime_tool: RuntimeCall,
    blueprint_id: str,
    *,
    overwrite: bool,
    timeout: float,
) -> dict[str, Any]:
    return call_runtime_tool(
        "marketplace_catalog_install",
        {"blueprint_id": blueprint_id, "overwrite": bool(overwrite)},
        timeout=timeout,
    )


def export_marketplace_bundle_via_mcp(call_runtime_tool: RuntimeCall, blueprint_id: str, *, timeout: float) -> dict[str, Any]:
    return call_runtime_tool("marketplace_bundle_export", {"blueprint_id": blueprint_id}, timeout=timeout)


def import_marketplace_bundle_via_mcp(
    call_runtime_tool: RuntimeCall,
    bundle_bytes: bytes,
    *,
    filename: str,
    overwrite: bool,
    timeout: float,
) -> dict[str, Any]:
    return call_runtime_tool(
        "marketplace_bundle_import",
        {
            "bundle_bytes_b64": base64.b64encode(bundle_bytes).decode("utf-8"),
            "filename": filename,
            "overwrite": bool(overwrite),
        },
        timeout=timeout,
    )
