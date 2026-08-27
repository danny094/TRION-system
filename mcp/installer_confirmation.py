"""Installer mutation postconditions for confirmed registry reloads."""

from collections.abc import Mapping
from typing import Any

from mcp.catalog_contracts import MCPRegistryReloadConfirmation
from mcp.installer_registry import registry_entry_from_config


class _Absent:
    pass


ABSENT = _Absent()


def require_registry_postcondition(
    confirmation: MCPRegistryReloadConfirmation,
    mcp_id: str,
    intended_config: Mapping[str, Any] | _Absent,
) -> None:
    if not isinstance(confirmation, MCPRegistryReloadConfirmation):
        raise TypeError("confirmation must be MCPRegistryReloadConfirmation")
    if not isinstance(mcp_id, str) or not mcp_id.strip():
        raise ValueError("mcp_id must be a non-empty string")
    published = confirmation.published_snapshot.desired_mcps
    if intended_config is ABSENT:
        if mcp_id in published:
            raise ValueError(f"Published registry still contains MCP '{mcp_id}'")
        return
    if not isinstance(intended_config, Mapping):
        raise TypeError("intended_config must be a mapping or ABSENT")
    expected = registry_entry_from_config(dict(intended_config))
    actual = published.get(mcp_id)
    if actual is None:
        raise ValueError(f"Published registry does not contain MCP '{mcp_id}'")
    if _plain(actual) != _plain(expected):
        raise ValueError(f"Published registry entry for MCP '{mcp_id}' does not match intended config")


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value
