"""Immutable canonical MCP tool-result contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
import math
from types import MappingProxyType
from typing import Any, Optional

from mcp.protocol_contracts import (
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus,
)


_MISSING = object()


class MCPToolCallStatus(Enum):
    SUCCESS = auto()
    TOOL_FAILURE = auto()
    PROTOCOL_FAILURE = auto()
    TRANSPORT_FAILURE = auto()


class MCPResultPresence(Enum):
    MISSING = auto()
    EMPTY = auto()
    VALUE = auto()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("mapping keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise TypeError("tool result numbers must be finite")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("tool result values must be recursively JSON-compatible")


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class MCPToolResultEnvelope:
    status: MCPToolCallStatus
    content_presence: MCPResultPresence = MCPResultPresence.MISSING
    content: Optional[tuple[Any, ...]] = None
    structured_content_presence: MCPResultPresence = MCPResultPresence.MISSING
    structured_content: Optional[Mapping[str, Any]] = None
    is_error_presence: MCPResultPresence = MCPResultPresence.MISSING
    is_error: Optional[bool] = None
    protocol_error: Optional[Mapping[str, Any]] = None
    transport_diagnostic: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPToolCallStatus):
            raise TypeError("status must be MCPToolCallStatus")
        self._validate_content()
        self._validate_structured_content()
        self._validate_is_error()
        self._validate_status()
        object.__setattr__(self, "content", _freeze(self.content))
        object.__setattr__(self, "structured_content", _freeze(self.structured_content))
        object.__setattr__(self, "protocol_error", _freeze(self.protocol_error))

    def _validate_content(self) -> None:
        if not isinstance(self.content_presence, MCPResultPresence):
            raise TypeError("content_presence must be MCPResultPresence")
        if self.content_presence is MCPResultPresence.MISSING:
            if self.content is not None:
                raise ValueError("missing content requires None")
        elif not isinstance(self.content, (list, tuple)):
            raise TypeError("present content must be a list or tuple")
        elif (self.content_presence is MCPResultPresence.EMPTY) != (len(self.content) == 0):
            raise ValueError("content presence contradicts its value")

    def _validate_structured_content(self) -> None:
        if not isinstance(self.structured_content_presence, MCPResultPresence):
            raise TypeError("structured_content_presence must be MCPResultPresence")
        if self.structured_content_presence is MCPResultPresence.MISSING:
            if self.structured_content is not None:
                raise ValueError("missing structuredContent requires None")
        elif not isinstance(self.structured_content, Mapping):
            raise TypeError("present structuredContent must be a mapping")
        elif (self.structured_content_presence is MCPResultPresence.EMPTY) != (
            len(self.structured_content) == 0
        ):
            raise ValueError("structuredContent presence contradicts its value")

    def _validate_is_error(self) -> None:
        if not isinstance(self.is_error_presence, MCPResultPresence):
            raise TypeError("is_error_presence must be MCPResultPresence")
        if self.is_error_presence is MCPResultPresence.EMPTY:
            raise ValueError("isError never permits EMPTY")
        if self.is_error_presence is MCPResultPresence.MISSING:
            if self.is_error is not None:
                raise ValueError("missing isError requires None")
        elif not isinstance(self.is_error, bool):
            raise TypeError("present isError must be bool")

    def _validate_status(self) -> None:
        result_present = any(
            presence is not MCPResultPresence.MISSING
            for presence in (
                self.content_presence,
                self.structured_content_presence,
                self.is_error_presence,
            )
        )
        if self.status in {MCPToolCallStatus.SUCCESS, MCPToolCallStatus.TOOL_FAILURE}:
            if self.protocol_error is not None or self.transport_diagnostic is not None:
                raise ValueError("tool results forbid protocol and transport diagnostics")
            expected_error = self.status is MCPToolCallStatus.TOOL_FAILURE
            if (self.is_error is True) != expected_error:
                raise ValueError("status contradicts isError")
        elif self.status is MCPToolCallStatus.PROTOCOL_FAILURE:
            if result_present or self.transport_diagnostic is not None:
                raise ValueError("protocol failure forbids result and transport fields")
            if self.protocol_error is not None and not isinstance(self.protocol_error, Mapping):
                raise TypeError("protocol_error must be a mapping")
        elif self.status is MCPToolCallStatus.TRANSPORT_FAILURE:
            if result_present or self.protocol_error is not None:
                raise ValueError("transport failure forbids result and protocol fields")
            if not isinstance(self.transport_diagnostic, str) or not self.transport_diagnostic:
                raise ValueError("transport failure requires a diagnostic")


def _presence(value: Any) -> MCPResultPresence:
    return MCPResultPresence.EMPTY if len(value) == 0 else MCPResultPresence.VALUE


def project_tool_result_envelope(outcome: MCPTransportRequestOutcome) -> MCPToolResultEnvelope:
    if not isinstance(outcome, MCPTransportRequestOutcome):
        raise TypeError("outcome must be MCPTransportRequestOutcome")
    if outcome.status is MCPTransportRequestStatus.TRANSPORT_FAILURE:
        return MCPToolResultEnvelope(
            MCPToolCallStatus.TRANSPORT_FAILURE,
            transport_diagnostic=outcome.transport_diagnostic,
        )
    if outcome.status is MCPTransportRequestStatus.PROTOCOL_FAILURE:
        return MCPToolResultEnvelope(
            MCPToolCallStatus.PROTOCOL_FAILURE,
            protocol_error=outcome.protocol_error,
        )
    payload = outcome.payload
    if not isinstance(payload, Mapping):
        return MCPToolResultEnvelope(MCPToolCallStatus.PROTOCOL_FAILURE)
    content = payload.get("content", _MISSING)
    structured = payload.get("structuredContent", _MISSING)
    is_error = payload.get("isError", _MISSING)
    if (content is not _MISSING and not isinstance(content, (list, tuple))) or (
        structured is not _MISSING and not isinstance(structured, Mapping)
    ) or (is_error is not _MISSING and not isinstance(is_error, bool)):
        return MCPToolResultEnvelope(MCPToolCallStatus.PROTOCOL_FAILURE)
    return MCPToolResultEnvelope(
        MCPToolCallStatus.TOOL_FAILURE if is_error is True else MCPToolCallStatus.SUCCESS,
        _presence(content) if content is not _MISSING else MCPResultPresence.MISSING,
        content if content is not _MISSING else None,
        _presence(structured) if structured is not _MISSING else MCPResultPresence.MISSING,
        structured if structured is not _MISSING else None,
        MCPResultPresence.VALUE if is_error is not _MISSING else MCPResultPresence.MISSING,
        is_error if is_error is not _MISSING else None,
    )


def project_tool_result_wire_mapping(envelope: MCPToolResultEnvelope) -> Mapping[str, Any]:
    if not isinstance(envelope, MCPToolResultEnvelope):
        raise TypeError("envelope must be MCPToolResultEnvelope")
    result = {}
    if envelope.content_presence is not MCPResultPresence.MISSING:
        result["content"] = _plain(envelope.content)
    if envelope.structured_content_presence is not MCPResultPresence.MISSING:
        result["structuredContent"] = _plain(envelope.structured_content)
    if envelope.is_error_presence is not MCPResultPresence.MISSING:
        result["isError"] = envelope.is_error
    if envelope.protocol_error is not None:
        result["error"] = _plain(envelope.protocol_error)
    if envelope.transport_diagnostic is not None:
        result["error"] = envelope.transport_diagnostic
    return MappingProxyType(result)
