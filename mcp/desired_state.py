"""Typed MCP registry-source and desired-state composition boundary."""

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import AbstractSet, Any

from mcp.catalog_contracts import MCPDesiredState


class MCPRegistrySourceStatus(str, Enum):
    MISSING = "MISSING"
    READ_FAILED = "READ_FAILED"
    PARSE_FAILED = "PARSE_FAILED"
    VALID = "VALID"


@dataclass(frozen=True)
class MCPRegistrySourceOutcome:
    status: MCPRegistrySourceStatus
    custom_registry: Mapping[str, Mapping[str, Any]] | None = None
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPRegistrySourceStatus):
            raise TypeError("status must be an MCPRegistrySourceStatus")
        if self.status is MCPRegistrySourceStatus.VALID:
            if not isinstance(self.custom_registry, Mapping):
                raise ValueError("VALID registry source requires custom data")
        elif self.custom_registry is not None:
            raise ValueError("Non-VALID registry source cannot carry custom data")

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

        if self.custom_registry is not None:
            validated = {}
            for mcp_id, config in self.custom_registry.items():
                if not isinstance(mcp_id, str) or not mcp_id.strip():
                    raise ValueError("Custom registry requires non-empty string identifiers")
                if not isinstance(config, Mapping):
                    raise TypeError(f"Configuration for {mcp_id!r} must be a mapping")
                validated[mcp_id] = freeze(config)
            object.__setattr__(self, "custom_registry", MappingProxyType(validated))


def load_registry_source(
    path: Path | None = None,
    *,
    core_ids: AbstractSet[str] = frozenset(),
) -> MCPRegistrySourceOutcome:
    """Classify registry bytes without converting failures into defaults."""
    if path is None:
        from mcp.config import get_registry_path

        path = get_registry_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return MCPRegistrySourceOutcome(MCPRegistrySourceStatus.MISSING)
    except (OSError, UnicodeError):
        return MCPRegistrySourceOutcome(
            MCPRegistrySourceStatus.READ_FAILED,
            diagnostic="registry_read_failed",
        )
    try:
        loaded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return MCPRegistrySourceOutcome(
            MCPRegistrySourceStatus.PARSE_FAILED,
            diagnostic="registry_json_invalid",
        )
    if not isinstance(loaded, dict) or not all(
        isinstance(name, str)
        and bool(name.strip())
        and isinstance(config, dict)
        for name, config in loaded.items()
    ):
        return MCPRegistrySourceOutcome(
            MCPRegistrySourceStatus.PARSE_FAILED,
            diagnostic="registry_shape_invalid",
        )
    if set(loaded).intersection(core_ids):
        return MCPRegistrySourceOutcome(
            MCPRegistrySourceStatus.PARSE_FAILED,
            diagnostic="core_custom_id_collision",
        )
    return MCPRegistrySourceOutcome(
        MCPRegistrySourceStatus.VALID,
        custom_registry=deepcopy(loaded),
    )


def compose_mcp_desired_state(
    core_defaults: Mapping[str, Mapping[str, Any]],
    source: MCPRegistrySourceOutcome,
) -> MCPDesiredState:
    """Compose only structurally valid, collision-free desired state."""
    if source.status is MCPRegistrySourceStatus.MISSING:
        custom: Mapping[str, Mapping[str, Any]] = {}
    elif source.status is MCPRegistrySourceStatus.VALID:
        custom = source.custom_registry or {}
    else:
        raise ValueError(f"Registry source status blocks composition: {source.status.name}")
    collision = set(core_defaults).intersection(custom)
    if collision:
        raise ValueError("Core and custom MCP identifiers must be disjoint")
    return MCPDesiredState(core_mcps=core_defaults, custom_mcps=custom)
