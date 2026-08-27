"""Contract tests for the canonical typed tools/list gate."""
from dataclasses import FrozenInstanceError, fields

import pytest

from mcp.protocol_contracts import (
    MCPHTTPRequestObservation,
    MCPSTDIORequestObservation,
    MCPToolsListProtocolResult,
    MCPToolsListProtocolStatus as ListStatus,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_tools_list import project_tools_list_response
from mcp.protocol_negotiation_contracts import SUPPORTED_MCP_PROTOCOL_VERSION, validate_protocol_version
from mcp.tool_result_contracts import MCPResultPresence as Presence, MCPToolCallStatus as ToolStatus, MCPToolResultEnvelope, project_tool_result_envelope
from mcp.transports import http_tools_list, sse_tools_list
from mcp.transports.http import HTTPTransport
from mcp.transports.sse import SSETransport
from mcp.transports.stdio import STDIOTransport

def _outcome(status, **values):
    return MCPTransportRequestOutcome(status=status, **values)

def test_status_spaces_and_outcome_fields_are_exact():
    assert {item.name for item in RequestStatus} == {"OK", "PROTOCOL_FAILURE", "TRANSPORT_FAILURE"}
    assert {item.name for item in FailureKind} == {"JSON_RPC_ERROR", "MALFORMED_RESPONSE"}
    assert {item.name for item in ListStatus} == {
        "SUCCESS_WITH_TOOLS", "SUCCESS_EMPTY", "PROTOCOL_FAILURE", "TRANSPORT_FAILURE"
    }
    assert [item.name for item in fields(MCPTransportRequestOutcome)] == [
        "status", "payload", "protocol_failure_kind", "protocol_error", "transport_diagnostic"
    ]
    assert not hasattr(_outcome(RequestStatus.OK, payload={}), "legacy_response")


@pytest.mark.parametrize(
    "values",
    [
        {"status": RequestStatus.OK},
        {"status": RequestStatus.OK, "payload": None},
        {"status": RequestStatus.OK, "payload": {}, "transport_diagnostic": "x"},
        {"status": RequestStatus.OK, "payload": {}, "protocol_error": {}},
        {"status": RequestStatus.PROTOCOL_FAILURE},
        {"status": RequestStatus.PROTOCOL_FAILURE, "protocol_failure_kind": FailureKind.JSON_RPC_ERROR},
        {"status": RequestStatus.PROTOCOL_FAILURE, "payload": {}, "protocol_failure_kind": FailureKind.JSON_RPC_ERROR, "protocol_error": {}},
        {"status": RequestStatus.PROTOCOL_FAILURE, "protocol_failure_kind": FailureKind.MALFORMED_RESPONSE, "protocol_error": {}},
        {"status": RequestStatus.PROTOCOL_FAILURE, "payload": {}, "protocol_failure_kind": FailureKind.MALFORMED_RESPONSE},
        {"status": RequestStatus.TRANSPORT_FAILURE},
        {"status": RequestStatus.TRANSPORT_FAILURE, "transport_diagnostic": ""},
        {"status": RequestStatus.TRANSPORT_FAILURE, "transport_diagnostic": "x", "payload": {}},
        {"status": RequestStatus.TRANSPORT_FAILURE, "transport_diagnostic": "x", "protocol_failure_kind": FailureKind.MALFORMED_RESPONSE},
    ],
)
def test_invalid_outcome_construction_fails_closed(values):
    with pytest.raises((TypeError, ValueError)):
        MCPTransportRequestOutcome(**values)


def test_recursive_immutability_and_frozen_instances():
    outcome = _outcome(RequestStatus.OK, payload={"nested": [{"value": 1}]})
    with pytest.raises(TypeError):
        outcome.payload["nested"] = ()
    with pytest.raises(TypeError):
        outcome.payload["nested"][0]["value"] = 2
    with pytest.raises(FrozenInstanceError):
        outcome.status = RequestStatus.TRANSPORT_FAILURE


def test_http_observation_and_legacy_projection():
    ok = MCPHTTPRequestObservation(_outcome(RequestStatus.OK, payload={"content": [], "structuredContent": {"value": 1}, "isError": False}))
    error = MCPHTTPRequestObservation(_outcome(
        RequestStatus.PROTOCOL_FAILURE,
        protocol_failure_kind=FailureKind.JSON_RPC_ERROR,
        protocol_error={"code": -1},
    ))
    malformed = MCPHTTPRequestObservation(_outcome(
        RequestStatus.PROTOCOL_FAILURE,
        protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
    ))
    transport = MCPHTTPRequestObservation(
        _outcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic="RuntimeError"), ""
    )
    assert project_tool_result_envelope(ok.outcome).status is ToolStatus.SUCCESS
    assert project_tool_result_envelope(error.outcome).status is ToolStatus.PROTOCOL_FAILURE
    assert project_tool_result_envelope(malformed.outcome).protocol_error is None
    assert project_tool_result_envelope(transport.outcome).status is ToolStatus.TRANSPORT_FAILURE
    with pytest.raises(ValueError):
        MCPHTTPRequestObservation(ok.outcome, "contradiction")


def test_stdio_observation_and_legacy_projection():
    observation = MCPSTDIORequestObservation(
        _outcome(RequestStatus.OK, payload={"content": [], "structuredContent": {"value": [1]}}),
        {"jsonrpc": "2.0", "id": 1, "result": {"content": [], "structuredContent": {"value": [1]}}},
    )
    envelope = project_tool_result_envelope(observation.outcome)
    assert envelope.content_presence is Presence.EMPTY
    assert envelope.structured_content_presence is Presence.VALUE
    assert envelope.structured_content["value"] == (1,)
    with pytest.raises(ValueError):
        MCPSTDIORequestObservation(observation.outcome, {"error": "contradiction"})


@pytest.mark.parametrize(
    ("outcome", "status", "tools"),
    [
        (_outcome(RequestStatus.OK, payload={"tools": [{"name": "demo"}]}), ListStatus.SUCCESS_WITH_TOOLS, ({"name": "demo"},)),
        (_outcome(RequestStatus.OK, payload={"tools": []}), ListStatus.SUCCESS_EMPTY, ()),
        (_outcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.MALFORMED_RESPONSE), ListStatus.PROTOCOL_FAILURE, ()),
        (_outcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic="offline"), ListStatus.TRANSPORT_FAILURE, ()),
        (_outcome(RequestStatus.OK, payload={"not_tools": []}), ListStatus.PROTOCOL_FAILURE, ()),
        (_outcome(RequestStatus.OK, payload={"tools": ["invalid"]}), ListStatus.PROTOCOL_FAILURE, ()),
    ],
)
def test_tools_list_projection_has_four_controlled_outcomes(outcome, status, tools):
    result = project_tools_list_response(outcome)
    assert result.status is status
    assert tuple(map(dict, result.tools)) == tools


def test_result_rejects_tools_outside_success_with_tools():
    with pytest.raises(ValueError):
        MCPToolsListProtocolResult(ListStatus.PROTOCOL_FAILURE, ({"name": "x"},))


@pytest.mark.parametrize("transport_class", (HTTPTransport, STDIOTransport, SSETransport))
def test_legacy_list_tools_is_retired_and_typed_facade_remains(transport_class):
    assert not hasattr(transport_class, "list_tools")
    assert hasattr(transport_class, "list_tools_protocol_result")


def test_transport_facades_delegate_to_their_typed_producers(monkeypatch):
    typed = MCPToolsListProtocolResult(ListStatus.SUCCESS_EMPTY)
    http = HTTPTransport("ignored")
    sse = SSETransport("ignored")
    sse._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    monkeypatch.setattr(http_tools_list, "list_tools_protocol_result", lambda transport: typed)
    monkeypatch.setattr(sse_tools_list, "list_tools_protocol_result", lambda transport: typed)
    assert http.list_tools_protocol_result() is typed
    assert sse.list_tools_protocol_result() is typed
    stdio = STDIOTransport("ignored")
    malformed = MCPSTDIORequestObservation(
        _outcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.MALFORMED_RESPONSE),
        {"result": None},
    )
    monkeypatch.setattr(stdio, "_send_request_outcome", lambda _payload: malformed)
    assert stdio.list_tools_protocol_result().status is ListStatus.PROTOCOL_FAILURE


@pytest.mark.parametrize(
    ("envelope", "status", "kind"),
    [
        ({"result": {"tools": []}}, RequestStatus.OK, None),
        ({"error": {"code": -1}}, RequestStatus.PROTOCOL_FAILURE, FailureKind.JSON_RPC_ERROR),
        ({"result": None}, RequestStatus.PROTOCOL_FAILURE, FailureKind.MALFORMED_RESPONSE),
    ],
)
def test_stdio_request_primitive_classifies_only_response_branches(monkeypatch, envelope, status, kind):
    transport = STDIOTransport("ignored")
    monkeypatch.setattr(transport, "_start_process", lambda: None)
    monkeypatch.setattr(transport, "_write_payload", lambda _payload: None)
    monkeypatch.setattr(transport, "_wait_for_response", lambda _timeout: envelope)
    observation = transport._send_request_outcome({})
    assert observation.outcome.status is status
    assert observation.outcome.protocol_failure_kind is kind


def test_diagnostic_text_never_overrides_transport_status():
    outcome = _outcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic="tools: success")
    assert project_tools_list_response(outcome).status is ListStatus.TRANSPORT_FAILURE


def test_stdio_send_adapter_preserves_call_tool_envelopes(monkeypatch):
    transport = STDIOTransport("ignored")
    success = MCPSTDIORequestObservation(_outcome(RequestStatus.OK, payload={"content": [], "structuredContent": {"value": 1}}), {"result": {"content": [], "structuredContent": {"value": 1}}})
    error = MCPSTDIORequestObservation(_outcome(RequestStatus.PROTOCOL_FAILURE, protocol_failure_kind=FailureKind.JSON_RPC_ERROR, protocol_error={"code": -1}), {"error": {"code": -1}})
    failure = MCPSTDIORequestObservation(_outcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic="Timeout"))
    cases = ((success, ToolStatus.SUCCESS), (error, ToolStatus.PROTOCOL_FAILURE), (failure, ToolStatus.TRANSPORT_FAILURE))
    for observation, expected_status in cases:
        monkeypatch.setattr(transport, "_send_request_outcome", lambda _payload, value=observation: value)
        envelope = transport.call_tool("demo", {})
        assert isinstance(envelope, MCPToolResultEnvelope)
        assert envelope.status is expected_status


def test_sse_list_split_does_not_change_call_tool(monkeypatch):
    source = SSETransport.call_tool
    transport = SSETransport("ignored")
    transport._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    response = type("Response", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"result": {"tools": []}},
    })()
    monkeypatch.setattr(sse_tools_list.requests, "post", lambda *_a, **_k: response)
    assert transport.list_tools_protocol_result().status is ListStatus.SUCCESS_EMPTY
    assert SSETransport.call_tool is source
