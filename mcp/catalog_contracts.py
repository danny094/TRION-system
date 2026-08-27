"""Immutable contracts shared by MCP desired state and catalog lifecycle."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType
from typing import Any

from mcp.protocol_contracts import MCPToolsListProtocolResult


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

    @property
    def all_mcps(self) -> Mapping[str, Mapping[str, Any]]:
        return MappingProxyType({**self.core_mcps, **self.custom_mcps})


class MCPTransportBindingStatus(Enum):
    BOUND = auto()
    DISABLED = auto()
    CONSTRUCTION_FAILED = auto()
    MISSING = auto()


class MCPDiscoveryStatus(Enum):
    PROTOCOL_RESULT = auto()
    DISABLED = auto()
    TRANSPORT_BINDING_FAILED = auto()
    TRANSPORT_MISSING = auto()
    DISCOVERY_NOT_RUN = auto()


@dataclass(frozen=True)
class MCPTransportBindingOutcome:
    status: MCPTransportBindingStatus
    transport: Any = None
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPTransportBindingStatus):
            raise TypeError("status must be MCPTransportBindingStatus")
        if self.status is MCPTransportBindingStatus.BOUND:
            if self.transport is None or self.diagnostic is not None:
                raise ValueError("BOUND requires one transport and no diagnostic")
        elif self.status is MCPTransportBindingStatus.DISABLED:
            if self.transport is not None or self.diagnostic is not None:
                raise ValueError("DISABLED forbids transport and diagnostic")
        elif self.status is MCPTransportBindingStatus.CONSTRUCTION_FAILED:
            if self.transport is not None or not isinstance(self.diagnostic, str) or not self.diagnostic:
                raise ValueError("CONSTRUCTION_FAILED requires exactly one diagnostic")
        elif self.transport is not None:
            raise ValueError("MISSING forbids transport")


@dataclass(frozen=True)
class MCPDiscoveryOutcome:
    status: MCPDiscoveryStatus
    protocol_result: MCPToolsListProtocolResult | None = None
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPDiscoveryStatus):
            raise TypeError("status must be MCPDiscoveryStatus")
        if self.status is MCPDiscoveryStatus.PROTOCOL_RESULT:
            if not isinstance(self.protocol_result, MCPToolsListProtocolResult):
                raise ValueError("PROTOCOL_RESULT requires a P13 protocol result")
        elif self.protocol_result is not None:
            raise ValueError("Only PROTOCOL_RESULT may carry a P13 result")


@dataclass(frozen=True)
class MCPToolCatalogSnapshot:
    desired_mcps: Mapping[str, Mapping[str, Any]]
    bindings_by_mcp: Mapping[str, MCPTransportBindingOutcome | None]
    discovery_by_mcp: Mapping[str, MCPDiscoveryOutcome | None]
    availability_by_mcp: Mapping[str, Mapping[str, Any]]
    routes_by_tool: Mapping[str, Mapping[str, Any]]
    quarantined_tools: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_parts(
        cls,
        desired_state: MCPDesiredState,
        bindings_by_mcp: Mapping[str, MCPTransportBindingOutcome | None],
        discovery_by_mcp: Mapping[str, MCPDiscoveryOutcome | None],
        availability_by_mcp: Mapping[str, Mapping[str, Any]],
        routes_by_tool: Mapping[str, Mapping[str, Any]],
        quarantined_tools: Mapping[str, tuple[str, ...]],
    ) -> "MCPToolCatalogSnapshot":
        return cls(
            desired_state.all_mcps,
            bindings_by_mcp,
            discovery_by_mcp,
            availability_by_mcp,
            routes_by_tool,
            quarantined_tools,
        )

    def __post_init__(self) -> None:
        ids = set(self.desired_mcps)
        if set(self.bindings_by_mcp) != ids or set(self.discovery_by_mcp) != ids or set(self.availability_by_mcp) != ids:
            raise ValueError("desired, binding, discovery and availability MCP ids must match")
        for tool_name, route in self.routes_by_tool.items():
            if route.get("tool_name") != tool_name or route.get("mcp_name") not in ids or route.get("transport") is None:
                raise ValueError("routes must bind tool name, MCP id and transport")
        object.__setattr__(self, "desired_mcps", _freeze(self.desired_mcps))
        object.__setattr__(self, "bindings_by_mcp", MappingProxyType(dict(self.bindings_by_mcp)))
        object.__setattr__(self, "discovery_by_mcp", MappingProxyType(dict(self.discovery_by_mcp)))
        object.__setattr__(self, "availability_by_mcp", _freeze(self.availability_by_mcp))
        object.__setattr__(self, "routes_by_tool", _freeze(self.routes_by_tool))
        object.__setattr__(self, "quarantined_tools", _freeze(self.quarantined_tools))


@dataclass(frozen=True)
class CatalogPublicationOutcome:
    snapshot: MCPToolCatalogSnapshot


@dataclass(frozen=True)
class CatalogRevocationOutcome:
    retired_count: int

@dataclass(frozen=True)
class MCPRegistryReloadConfirmation:
    published_snapshot: MCPToolCatalogSnapshot
    revocation: CatalogRevocationOutcome

    def __post_init__(self) -> None:
        if not isinstance(self.published_snapshot, MCPToolCatalogSnapshot):
            raise TypeError("published_snapshot must be MCPToolCatalogSnapshot")
        if not isinstance(self.revocation, CatalogRevocationOutcome):
            raise TypeError("revocation must be CatalogRevocationOutcome")

@dataclass(frozen=True)
class CatalogLease:
    release: Any


@dataclass(frozen=True)
class MCPCallToken:
    tool_name: str
    mcp_name: str
    transport: Any
    tool_definition: Mapping[str, Any]
    lease: CatalogLease


def make_route(tool_name: str, mcp_name: str, transport: Any, tool_definition: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({"tool_name": tool_name, "mcp_name": mcp_name, "transport": transport, "tool_definition": MappingProxyType(dict(tool_definition))})


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value
