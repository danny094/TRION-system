"""Immutable MCP protocol negotiation contracts."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


SUPPORTED_MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPProtocolNegotiationStatus(Enum):
    NEGOTIATED = auto()
    MISSING = auto()
    MALFORMED = auto()
    UNSUPPORTED = auto()


@dataclass(frozen=True)
class MCPProtocolNegotiationResult:
    status: MCPProtocolNegotiationStatus
    protocol_version: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPProtocolNegotiationStatus):
            raise TypeError("status must be MCPProtocolNegotiationStatus")
        if self.status is MCPProtocolNegotiationStatus.NEGOTIATED:
            if self.protocol_version != SUPPORTED_MCP_PROTOCOL_VERSION:
                raise ValueError("NEGOTIATED requires the supported protocol version")
        elif self.status is MCPProtocolNegotiationStatus.UNSUPPORTED:
            if not isinstance(self.protocol_version, str) or not self.protocol_version:
                raise ValueError("UNSUPPORTED requires the original protocol version")
            if self.protocol_version == SUPPORTED_MCP_PROTOCOL_VERSION:
                raise ValueError("UNSUPPORTED forbids the supported protocol version")
        elif self.protocol_version is not None:
            raise ValueError("missing and malformed results forbid a protocol version")


def validate_protocol_version(value: object) -> MCPProtocolNegotiationResult:
    if value is None:
        status = MCPProtocolNegotiationStatus.MISSING
        return MCPProtocolNegotiationResult(status)
    if not isinstance(value, str) or not value:
        status = MCPProtocolNegotiationStatus.MALFORMED
        return MCPProtocolNegotiationResult(status)
    if value != SUPPORTED_MCP_PROTOCOL_VERSION:
        status = MCPProtocolNegotiationStatus.UNSUPPORTED
        return MCPProtocolNegotiationResult(status, value)
    return MCPProtocolNegotiationResult(MCPProtocolNegotiationStatus.NEGOTIATED, value)
