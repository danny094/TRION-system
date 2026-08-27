from dataclasses import FrozenInstanceError
import socket

import pytest

from mcp.structural_validation_contracts import (
    MCPStructuralValidationResult,
    MCPStructuralValidationStatus as Status,
)
from mcp.structural_validator import validate_structured_output
from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)


_MISSING = object()


def _success(structured_content=_MISSING) -> MCPToolResultEnvelope:
    if structured_content is _MISSING:
        return MCPToolResultEnvelope(ToolStatus.SUCCESS)
    presence = Presence.EMPTY if not structured_content else Presence.VALUE
    return MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=presence,
        structured_content=structured_content,
    )


def _tool_failure() -> MCPToolResultEnvelope:
    return MCPToolResultEnvelope(
        ToolStatus.TOOL_FAILURE,
        is_error_presence=Presence.VALUE,
        is_error=True,
    )


def test_result_is_immutable_and_retains_the_original_envelope():
    envelope = _success({"value": 1})
    result = MCPStructuralValidationResult(Status.VALID, envelope)

    assert result.envelope is envelope
    with pytest.raises(FrozenInstanceError):
        result.status = Status.INSTANCE_MISMATCH


@pytest.mark.parametrize(
    ("schema", "structured_content"),
    [
        ({"type": "object", "required": ["value"]}, {"value": 1}),
        ({"type": "object", "maxProperties": 0}, {}),
    ],
)
def test_validates_value_and_empty_mapping_instances(schema, structured_content):
    result = validate_structured_output(schema, _success(structured_content))

    assert result.status is Status.VALID


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        (None, Status.OUTPUT_SCHEMA_MISSING),
        ([], Status.OUTPUT_SCHEMA_MALFORMED),
        ({"type": 3}, Status.OUTPUT_SCHEMA_MALFORMED),
        (
            {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object"},
            Status.OUTPUT_SCHEMA_UNSUPPORTED,
        ),
    ],
)
def test_schema_failures_are_typed(schema, expected):
    result = validate_structured_output(schema, _success({}))

    assert result.status is expected


def test_missing_structured_content_is_distinct_from_empty():
    result = validate_structured_output({"type": "object"}, _success())

    assert result.status is Status.STRUCTURED_CONTENT_MISSING


def test_instance_mismatch_is_typed():
    result = validate_structured_output(
        {"type": "object", "required": ["value"]},
        _success({}),
    )

    assert result.status is Status.INSTANCE_MISMATCH


def test_remote_reference_is_rejected_offline(monkeypatch):
    def _network_forbidden(*_args, **_kwargs):
        raise AssertionError("structural validation attempted network access")

    monkeypatch.setattr(socket, "getaddrinfo", _network_forbidden)
    result = validate_structured_output(
        {"$ref": "https://example.invalid/schema"},
        _success({}),
    )

    assert result.status is Status.OUTPUT_SCHEMA_UNSUPPORTED


def test_internal_reference_remains_supported_offline():
    result = validate_structured_output(
        {
            "$defs": {"payload": {"type": "object", "required": ["value"]}},
            "$ref": "#/$defs/payload",
        },
        _success({"value": 1}),
    )

    assert result.status is Status.VALID


@pytest.mark.parametrize(
    ("envelope", "expected"),
    [
        (_tool_failure(), Status.TOOL_FAILURE),
        (MCPToolResultEnvelope(ToolStatus.PROTOCOL_FAILURE), Status.PROTOCOL_FAILURE),
        (
            MCPToolResultEnvelope(ToolStatus.TRANSPORT_FAILURE, transport_diagnostic="offline"),
            Status.TRANSPORT_FAILURE,
        ),
    ],
)
def test_envelope_failure_status_has_priority_over_schema(envelope, expected):
    result = validate_structured_output(None, envelope)

    assert result.status is expected


def test_result_contract_rejects_status_that_contradicts_envelope():
    with pytest.raises(ValueError):
        MCPStructuralValidationResult(Status.VALID, _tool_failure())
