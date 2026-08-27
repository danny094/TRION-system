"""Immutable P13 transport and tools/list protocol contracts."""

from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType
from typing import Any, Mapping, Optional


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _plain_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_value(item) for item in value]
    if isinstance(value, frozenset):
        return {_plain_value(item) for item in value}
    return value


class MCPTransportRequestStatus(Enum):
    OK = auto()
    PROTOCOL_FAILURE = auto()
    TRANSPORT_FAILURE = auto()


class MCPTransportProtocolFailureKind(Enum):
    JSON_RPC_ERROR = auto()
    MALFORMED_RESPONSE = auto()


class MCPToolsListProtocolStatus(Enum):
    SUCCESS_WITH_TOOLS = auto()
    SUCCESS_EMPTY = auto()
    PROTOCOL_FAILURE = auto()
    TRANSPORT_FAILURE = auto()


class MCPSTDIOReadStatus(Enum):
    JSON_MESSAGE = auto()
    MALFORMED_RESPONSE = auto()
    READ_FAILURE = auto()
    READ_TIMEOUT = auto()


@dataclass(frozen=True)
class MCPTransportRequestOutcome:
    status: MCPTransportRequestStatus
    payload: Optional[object] = None
    protocol_failure_kind: Optional[MCPTransportProtocolFailureKind] = None
    protocol_error: Optional[Mapping[str, object]] = None
    transport_diagnostic: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPTransportRequestStatus):
            raise TypeError("status must be MCPTransportRequestStatus")
        if self.status is MCPTransportRequestStatus.OK:
            if (
                self.payload is None
                or self.protocol_failure_kind is not None
                or self.protocol_error is not None
                or self.transport_diagnostic is not None
            ):
                raise ValueError("OK requires only a non-None payload")
        elif self.status is MCPTransportRequestStatus.PROTOCOL_FAILURE:
            if self.payload is not None or self.transport_diagnostic is not None:
                raise ValueError("protocol failure forbids payload and transport diagnostic")
            if self.protocol_failure_kind is MCPTransportProtocolFailureKind.JSON_RPC_ERROR:
                if not isinstance(self.protocol_error, Mapping):
                    raise ValueError("JSON_RPC_ERROR requires the original mapping")
            elif self.protocol_failure_kind is MCPTransportProtocolFailureKind.MALFORMED_RESPONSE:
                if self.protocol_error is not None:
                    raise ValueError("MALFORMED_RESPONSE forbids protocol_error")
            else:
                raise ValueError("protocol failure requires a controlled failure kind")
        elif self.status is MCPTransportRequestStatus.TRANSPORT_FAILURE:
            if self.payload is not None or self.protocol_failure_kind is not None or self.protocol_error is not None:
                raise ValueError("transport failure forbids protocol fields and payload")
            if not isinstance(self.transport_diagnostic, str) or not self.transport_diagnostic:
                raise ValueError("transport failure requires one non-empty diagnostic")
        object.__setattr__(self, "payload", _freeze_value(self.payload))
        object.__setattr__(self, "protocol_error", _freeze_value(self.protocol_error))


@dataclass(frozen=True)
class MCPSTDIOReadObservation:
    status: MCPSTDIOReadStatus
    payload: Optional[Mapping[str, object]] = None
    transport_diagnostic: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPSTDIOReadStatus):
            raise TypeError("status must be MCPSTDIOReadStatus")
        if self.status is MCPSTDIOReadStatus.JSON_MESSAGE:
            if not isinstance(self.payload, Mapping) or self.transport_diagnostic is not None:
                raise ValueError("JSON_MESSAGE requires only a mapping payload")
            if not all(isinstance(key, str) for key in self.payload):
                raise ValueError("JSON_MESSAGE payload keys must be strings")
        elif self.status is MCPSTDIOReadStatus.MALFORMED_RESPONSE:
            if self.payload is not None or self.transport_diagnostic is not None:
                raise ValueError("MALFORMED_RESPONSE forbids payload and diagnostic")
        elif self.status in {MCPSTDIOReadStatus.READ_FAILURE, MCPSTDIOReadStatus.READ_TIMEOUT}:
            if self.payload is not None:
                raise ValueError("read transport status forbids payload")
            if not isinstance(self.transport_diagnostic, str) or not self.transport_diagnostic:
                raise ValueError("read transport status requires one non-empty diagnostic")
        object.__setattr__(self, "payload", _freeze_value(self.payload))


@dataclass(frozen=True)
class MCPHTTPRequestObservation:
    outcome: MCPTransportRequestOutcome
    transport_error_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, MCPTransportRequestOutcome):
            raise TypeError("outcome must be MCPTransportRequestOutcome")
        is_transport = self.outcome.status is MCPTransportRequestStatus.TRANSPORT_FAILURE
        if (is_transport and not isinstance(self.transport_error_text, str)) or (
            not is_transport and self.transport_error_text is not None
        ):
            raise ValueError("transport error text exists exactly for TRANSPORT_FAILURE")


@dataclass(frozen=True)
class MCPSTDIORequestObservation:
    outcome: MCPTransportRequestOutcome
    raw_envelope: Optional[Mapping[str, object]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, MCPTransportRequestOutcome):
            raise TypeError("STDIO observation requires outcome")
        outcome = self.outcome
        if self.raw_envelope is not None and not isinstance(self.raw_envelope, Mapping):
            raise TypeError("STDIO raw envelope must be mapping")
        envelope = _plain_value(self.raw_envelope or {})
        if outcome.status is MCPTransportRequestStatus.OK:
            valid = self.raw_envelope is None or (
                envelope.get("result") is not None and envelope["result"] == _plain_value(outcome.payload)
            )
        elif outcome.protocol_failure_kind is MCPTransportProtocolFailureKind.JSON_RPC_ERROR:
            valid = self.raw_envelope is None or (
                isinstance(envelope.get("error"), Mapping) and envelope["error"] == _plain_value(outcome.protocol_error)
            )
        elif outcome.protocol_failure_kind is MCPTransportProtocolFailureKind.MALFORMED_RESPONSE:
            valid = self.raw_envelope is None or (
                envelope.get("result") is None and not isinstance(envelope.get("error"), Mapping)
            )
        else:
            valid = self.raw_envelope is None or (
                set(envelope) == {"error"} and isinstance(envelope.get("error"), str)
            )
        if not valid:
            raise ValueError("STDIO envelope contradicts canonical outcome")
        object.__setattr__(self, "raw_envelope", _freeze_value(self.raw_envelope))


@dataclass(frozen=True)
class MCPToolsListProtocolResult:
    status: MCPToolsListProtocolStatus
    tools: tuple[Mapping[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, MCPToolsListProtocolStatus):
            raise TypeError("status must be MCPToolsListProtocolStatus")
        if not isinstance(self.tools, (list, tuple)) or not all(isinstance(tool, Mapping) for tool in self.tools):
            raise TypeError("tools must contain raw mapping definitions")
        tools = tuple(_freeze_value(tool) for tool in self.tools)
        if self.status is MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS:
            if not tools:
                raise ValueError("SUCCESS_WITH_TOOLS requires tools")
        elif tools:
            raise ValueError("only SUCCESS_WITH_TOOLS may carry tools")
        object.__setattr__(self, "tools", tools)
