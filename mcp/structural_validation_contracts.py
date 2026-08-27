"""Immutable MCP structured-output validation contracts."""

from dataclasses import dataclass
from enum import Enum, auto

from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope


class MCPStructuralValidationStatus(Enum):
    VALID = auto()
    OUTPUT_SCHEMA_MISSING = auto()
    OUTPUT_SCHEMA_MALFORMED = auto()
    OUTPUT_SCHEMA_UNSUPPORTED = auto()
    STRUCTURED_CONTENT_MISSING = auto()
    INSTANCE_MISMATCH = auto()
    TOOL_FAILURE = auto()
    PROTOCOL_FAILURE = auto()
    TRANSPORT_FAILURE = auto()


@dataclass(frozen=True)
class MCPStructuralValidationResult:
    status: MCPStructuralValidationStatus
    envelope: MCPToolResultEnvelope

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPStructuralValidationStatus):
            raise TypeError("status must be MCPStructuralValidationStatus")
        if not isinstance(self.envelope, MCPToolResultEnvelope):
            raise TypeError("envelope must be MCPToolResultEnvelope")
        expected = self._failure_status(self.envelope.status)
        if expected is None:
            if self.status in {
                MCPStructuralValidationStatus.TOOL_FAILURE,
                MCPStructuralValidationStatus.PROTOCOL_FAILURE,
                MCPStructuralValidationStatus.TRANSPORT_FAILURE,
            }:
                raise ValueError("successful envelope forbids a transport failure status")
        elif self.status is not expected:
            raise ValueError("structural status contradicts the envelope status")

    @classmethod
    def from_envelope_failure(
        cls,
        envelope: MCPToolResultEnvelope,
    ) -> "MCPStructuralValidationResult":
        if not isinstance(envelope, MCPToolResultEnvelope):
            raise TypeError("envelope must be MCPToolResultEnvelope")
        status = cls._failure_status(envelope.status)
        if status is None:
            raise ValueError("successful envelope is not a failure")
        return cls(status, envelope)

    @staticmethod
    def _failure_status(
        status: MCPToolCallStatus,
    ) -> MCPStructuralValidationStatus | None:
        if status is MCPToolCallStatus.SUCCESS:
            return None
        if status is MCPToolCallStatus.TOOL_FAILURE:
            return MCPStructuralValidationStatus.TOOL_FAILURE
        if status is MCPToolCallStatus.PROTOCOL_FAILURE:
            return MCPStructuralValidationStatus.PROTOCOL_FAILURE
        if status is MCPToolCallStatus.TRANSPORT_FAILURE:
            return MCPStructuralValidationStatus.TRANSPORT_FAILURE
        raise ValueError("unsupported MCP tool-call status")
