"""Publish, acquire and revoke MCP catalog snapshots."""

import threading
from typing import Callable

from mcp.catalog_contracts import (
    CatalogLease,
    CatalogPublicationOutcome,
    CatalogRevocationOutcome,
    MCPCallToken,
    MCPToolCatalogSnapshot,
)

_lock = threading.RLock()
_drained = threading.Condition(_lock)
_published_snapshot: MCPToolCatalogSnapshot | None = None
_acquires_stopped = True
_active_tokens = 0


def publish_catalog(snapshot: MCPToolCatalogSnapshot) -> CatalogPublicationOutcome:
    global _published_snapshot, _acquires_stopped
    with _lock:
        _published_snapshot = snapshot
        _acquires_stopped = False
    return CatalogPublicationOutcome(snapshot)


def current_catalog_snapshot() -> MCPToolCatalogSnapshot | None:
    with _lock:
        return _published_snapshot


def acquire_route(tool_name: str) -> MCPCallToken:
    global _active_tokens
    with _lock:
        if _acquires_stopped:
            raise RuntimeError("catalog routes are revoked")
        snapshot = _published_snapshot
        route = snapshot.routes_by_tool.get(tool_name) if snapshot else None
        if route is None:
            raise KeyError(tool_name)
        _active_tokens += 1
        released = False

        def release_once() -> None:
            nonlocal released
            with _lock:
                if released:
                    return
                released = True
            _release_token()

        lease = CatalogLease(release=release_once)
        return MCPCallToken(
            tool_name=tool_name,
            mcp_name=route["mcp_name"],
            transport=route["transport"],
            tool_definition=route["tool_definition"],
            lease=lease,
        )


def revoke_catalog_routes(
    retire_transport: Callable[[object], None],
    replacement_snapshot: MCPToolCatalogSnapshot | None = None,
) -> CatalogRevocationOutcome:
    global _published_snapshot, _acquires_stopped
    with _lock:
        _acquires_stopped = True
        while _active_tokens:
            _drained.wait()
        old_snapshot = _published_snapshot
        if replacement_snapshot is None:
            _published_snapshot = None
        else:
            publish_catalog(replacement_snapshot)
    retired = 0
    retired_transports = []
    retirement_errors = []
    for transport in _snapshot_transports(old_snapshot):
        if any(retired_transport is transport for retired_transport in retired_transports):
            continue
        retired_transports.append(transport)
        try:
            retire_transport(transport)
        except Exception as exc:
            retirement_errors.append(exc)
        else:
            retired += 1
    if retirement_errors:
        raise ExceptionGroup("MCP transport retirement failed", retirement_errors)
    return CatalogRevocationOutcome(retired)


def _release_token() -> None:
    global _active_tokens
    with _lock:
        if _active_tokens == 0:
            return
        _active_tokens -= 1
        if _active_tokens == 0:
            _drained.notify_all()


def _snapshot_transports(snapshot):
    if snapshot is None:
        return []
    transports = []
    for binding in snapshot.bindings_by_mcp.values():
        transport = getattr(binding, "transport", None)
        if transport is not None and all(existing is not transport for existing in transports):
            transports.append(transport)
    for route in snapshot.routes_by_tool.values():
        transport = route["transport"]
        if all(existing is not transport for existing in transports):
            transports.append(transport)
    return transports
