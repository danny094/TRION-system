"""Immutable contracts shared with the future MCP catalog builder."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class MCPDesiredState:
    """Core defaults and validated custom entries before discovery."""

    core_mcps: Mapping[str, Mapping[str, Any]]
    custom_mcps: Mapping[str, Mapping[str, Any]]

    def __post_init__(self) -> None:
        def freeze(value: Any) -> Any:
            if isinstance(value, Mapping):
                return MappingProxyType({key: freeze(item) for key, item in value.items()})
            if isinstance(value, list):
                return tuple(freeze(item) for item in value)
            if isinstance(value, tuple):
                return tuple(freeze(item) for item in value)
            if isinstance(value, (set, frozenset)):
                return frozenset(freeze(item) for item in value)
            return value

        def validated_mcps(name: str, value: Any) -> Mapping[str, Mapping[str, Any]]:
            if not isinstance(value, Mapping):
                raise TypeError(f"{name} must be a mapping")
            validated = {}
            for mcp_id, config in value.items():
                if not isinstance(mcp_id, str) or not mcp_id.strip():
                    raise ValueError(f"{name} requires non-empty string identifiers")
                if not isinstance(config, Mapping):
                    raise TypeError(f"Configuration for {mcp_id!r} must be a mapping")
                validated[mcp_id] = freeze(config)
            return MappingProxyType(validated)

        core_mcps = validated_mcps("core_mcps", self.core_mcps)
        custom_mcps = validated_mcps("custom_mcps", self.custom_mcps)
        if set(core_mcps).intersection(custom_mcps):
            raise ValueError("Core and custom MCP identifiers must be disjoint")
        object.__setattr__(self, "core_mcps", core_mcps)
        object.__setattr__(self, "custom_mcps", custom_mcps)
