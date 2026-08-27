"""Adversarial local guards for the STDIO read/protocol gate."""

from dataclasses import fields

import pytest

from mcp.protocol_contracts import (
    MCPSTDIOReadObservation,
    MCPSTDIOReadStatus as ReadStatus,
    MCPSTDIORequestObservation,
    MCPToolsListProtocolStatus as ListStatus,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.tool_result_contracts import MCPResultPresence as Presence, MCPToolCallStatus as ToolStatus, MCPToolResultEnvelope, project_tool_result_envelope
from mcp.transports.http import HTTPTransport
from mcp.transports.sse import SSETransport
from mcp.transports.stdio import STDIOTransport
from mcp.transports.stdio_read import parse_stdio_read_line


def _outcome(status, **values):
    return MCPTransportRequestOutcome(status=status, **values)


def _stdio_observation(status, **values):
    return MCPSTDIOReadObservation(status=status, **values)


def _transport_with_observation(monkeypatch, observation):
    transport = STDIOTransport("ignored")
    monkeypatch.setattr(transport, "_start_process", lambda: None)
    monkeypatch.setattr(transport, "_write_payload", lambda _payload: None)
    monkeypatch.setattr(transport, "_wait_for_response", lambda _timeout: observation)
    return transport


def test_read_status_space_and_fields_are_exact():
    assert {item.name for item in ReadStatus} == {
        "JSON_MESSAGE",
        "MALFORMED_RESPONSE",
        "READ_FAILURE",
        "READ_TIMEOUT",
    }
    assert [item.name for item in fields(MCPSTDIOReadObservation)] == [
        "status",
        "payload",
        "transport_diagnostic",
    ]


@pytest.mark.parametrize(
    "values",
    [
        {"status": "READ_TIMEOUT", "transport_diagnostic": "x"},
        {"status": ReadStatus.JSON_MESSAGE},
        {"status": ReadStatus.JSON_MESSAGE, "payload": []},
        {"status": ReadStatus.JSON_MESSAGE, "payload": {}, "transport_diagnostic": "x"},
        {"status": ReadStatus.MALFORMED_RESPONSE, "payload": {}},
        {"status": ReadStatus.MALFORMED_RESPONSE, "transport_diagnostic": "x"},
        {"status": ReadStatus.READ_FAILURE},
        {"status": ReadStatus.READ_FAILURE, "transport_diagnostic": ""},
        {"status": ReadStatus.READ_FAILURE, "payload": {}, "transport_diagnostic": "x"},
        {"status": ReadStatus.READ_TIMEOUT},
        {"status": ReadStatus.READ_TIMEOUT, "transport_diagnostic": ""},
        {"status": ReadStatus.READ_TIMEOUT, "payload": {}, "transport_diagnostic": "x"},
    ],
)
def test_read_observation_rejects_invalid_construction(values):
    with pytest.raises((TypeError, ValueError)):
        MCPSTDIOReadObservation(**values)


@pytest.mark.parametrize("line", ["not json", "[1, 2]", "null", '"text"'])
def test_invalid_or_non_mapping_json_is_malformed(line):
    observation = parse_stdio_read_line(line)
    assert observation.status is ReadStatus.MALFORMED_RESPONSE
    assert observation.payload is None
    assert observation.transport_diagnostic is None


def test_valid_mapping_json_is_immutable_message():
    observation = parse_stdio_read_line('{"result": {"nested": [1]}}')
    assert observation.status is ReadStatus.JSON_MESSAGE
    assert observation.payload["result"]["nested"] == (1,)
    with pytest.raises(TypeError):
        observation.payload["result"] = {}


@pytest.mark.parametrize(
    ("read_observation", "status", "kind"),
    [
        (_stdio_observation(ReadStatus.MALFORMED_RESPONSE), RequestStatus.PROTOCOL_FAILURE, FailureKind.MALFORMED_RESPONSE),
        (_stdio_observation(ReadStatus.JSON_MESSAGE, payload={"result": {"value": 1}}), RequestStatus.OK, None),
        (_stdio_observation(ReadStatus.JSON_MESSAGE, payload={"error": {"code": -32000}}), RequestStatus.PROTOCOL_FAILURE, FailureKind.JSON_RPC_ERROR),
        (_stdio_observation(ReadStatus.JSON_MESSAGE, payload={"meta": 1}), RequestStatus.PROTOCOL_FAILURE, FailureKind.MALFORMED_RESPONSE),
    ],
)
def test_request_outcome_maps_read_observations(monkeypatch, read_observation, status, kind):
    transport = _transport_with_observation(monkeypatch, read_observation)
    observation = transport._send_request_outcome({})
    assert observation.outcome.status is status
    assert observation.outcome.protocol_failure_kind is kind


def test_malformed_call_tool_and_typed_list_result(monkeypatch):
    transport = _transport_with_observation(monkeypatch, _stdio_observation(ReadStatus.MALFORMED_RESPONSE))
    envelope = transport.call_tool("demo", {})
    assert isinstance(envelope, MCPToolResultEnvelope)
    assert envelope.status is ToolStatus.PROTOCOL_FAILURE
    assert envelope.content_presence is Presence.MISSING
    assert transport.list_tools_protocol_result().status is ListStatus.PROTOCOL_FAILURE


def test_legacy_list_tools_is_absent_and_typed_facades_remain():
    for transport_class in (HTTPTransport, STDIOTransport, SSETransport):
        assert not hasattr(transport_class, "list_tools")
        assert hasattr(transport_class, "list_tools_protocol_result")


def test_true_queue_timeout_is_transport_failure(monkeypatch):
    transport = _transport_with_observation(
        monkeypatch,
        _stdio_observation(ReadStatus.READ_TIMEOUT, transport_diagnostic="Timeout waiting for response"),
    )
    observation = transport._send_request_outcome({})
    assert observation.outcome.status is RequestStatus.TRANSPORT_FAILURE
    assert observation.outcome.transport_diagnostic == "Timeout waiting for response"


def test_original_json_rpc_error_mapping_is_preserved(monkeypatch):
    error = {"code": -32601, "message": "missing"}
    transport = _transport_with_observation(monkeypatch, _stdio_observation(ReadStatus.JSON_MESSAGE, payload={"error": error}))
    observation = transport._send_request_outcome({})
    assert observation.outcome.protocol_failure_kind is FailureKind.JSON_RPC_ERROR
    assert dict(observation.outcome.protocol_error) == error
    envelope = transport.call_tool("demo", {})
    assert envelope.status is ToolStatus.PROTOCOL_FAILURE
    assert dict(envelope.protocol_error) == error


def test_start_process_failure_is_controlled_transport_failure(monkeypatch):
    transport = STDIOTransport("ignored")
    monkeypatch.setattr(transport, "_start_process", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    observation = transport._send_request_outcome({})
    assert observation.outcome.status is RequestStatus.TRANSPORT_FAILURE
    assert observation.outcome.transport_diagnostic == "boom"


def test_invalid_initialize_response_is_not_timeout(monkeypatch):
    transport = _transport_with_observation(monkeypatch, _stdio_observation(ReadStatus.MALFORMED_RESPONSE))
    with pytest.raises(Exception) as excinfo:
        transport._initialize_process()
    assert "Malformed MCP response" in str(excinfo.value)
    assert "Timeout" not in str(excinfo.value)


def test_list_tools_protocol_result_does_not_leak_exception(monkeypatch):
    transport = _transport_with_observation(monkeypatch, _stdio_observation(ReadStatus.MALFORMED_RESPONSE))
    assert transport.list_tools_protocol_result().status is ListStatus.PROTOCOL_FAILURE


def test_no_canonical_legacy_contradiction_for_malformed():
    outcome = _outcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.MALFORMED_RESPONSE)
    observation = MCPSTDIORequestObservation(outcome)
    envelope = project_tool_result_envelope(observation.outcome)
    assert envelope.status is ToolStatus.PROTOCOL_FAILURE
    assert envelope.protocol_error is None
    with pytest.raises((TypeError, ValueError)):
        MCPSTDIORequestObservation(outcome, {"result": {"legacy": "success"}})
