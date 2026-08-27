"""Local parity guards for the behavior-neutral HTTP transport split."""
from pathlib import Path

import pytest

from mcp.protocol_contracts import (
    MCPHTTPRequestObservation,
    MCPTransportRequestOutcome,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_negotiation_contracts import SUPPORTED_MCP_PROTOCOL_VERSION, MCPProtocolNegotiationStatus as NegotiationStatus, validate_protocol_version
from mcp.tool_result_contracts import MCPResultPresence as Presence, MCPToolCallStatus as ToolStatus, MCPToolResultEnvelope, project_tool_result_envelope
from mcp.transports import http_request, http_response, http_session
from mcp.transports.http import HTTPTransport
class _Response:
    def __init__(self, payload=None, *, status=200, content_type="application/json", lines=(), error=None):
        self.payload = payload
        self.status_code = status
        self.headers = {"Content-Type": content_type}
        self._lines = lines
        self._error = error

    def json(self):
        if self._error:
            raise self._error
        return self.payload

    def iter_lines(self):
        return iter(self._lines)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")
def _transport():
    transport = HTTPTransport("http://local.invalid/mcp", "secret", timeout=7)
    transport._format = transport.FORMAT_JSON
    transport._format_detected = True
    transport._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    return transport
def test_http_facades_delegate_to_split_helpers(monkeypatch):
    transport = _transport()
    sentinels = {
        "get_base_headers": {"base": "ok"},
        "get_headers_with_session": {"session": "ok"},
        "detect_format": "json",
        "initialize_session": True,
        "ensure_session": True,
    }
    modules = {name: http_session for name in sentinels}
    methods = {
        "get_base_headers": "_get_base_headers",
        "get_headers_with_session": "_get_headers_with_session",
        "detect_format": "_detect_format",
        "initialize_session": "_initialize_session",
        "ensure_session": "_ensure_session",
    }
    for helper, module in modules.items():
        monkeypatch.setattr(module, helper, lambda *_a, _v=sentinels[helper], **_k: _v)
        assert getattr(transport, methods[helper])() == sentinels[helper]
    observation = MCPHTTPRequestObservation(MCPTransportRequestOutcome(RequestStatus.OK, payload={"content": []}))
    monkeypatch.setattr(http_request, "smart_request", lambda *_a, **_k: observation)
    assert http_request.smart_request(transport, {}).outcome is observation.outcome
    assert transport.call_tool("demo", {}) == project_tool_result_envelope(observation.outcome)
def test_headers_and_content_extraction_preserve_behavior():
    transport = _transport()
    assert transport._get_base_headers() == {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer secret",
    }
    transport._session_id = "session-1"
    assert transport._get_headers_with_session()["Mcp-Session-Id"] == "session-1"
    payload = {"content": [{"type": "text", "text": '{"value": 3}'}], "structuredContent": {"value": 3}, "isError": False}
    outcome = http_response.parse_response_outcome(_Response({"result": payload})).outcome
    envelope = project_tool_result_envelope(outcome)
    assert [dict(item) for item in outcome.payload["content"]] == payload["content"]
    assert dict(outcome.payload["structuredContent"]) == payload["structuredContent"]
    assert outcome.payload["isError"] is payload["isError"]
    with pytest.raises(TypeError): outcome.payload["structuredContent"]["value"] = 4
    assert envelope.content_presence is Presence.VALUE
    assert envelope.structured_content_presence is Presence.VALUE
    assert envelope.is_error is False
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (_Response({}, content_type="application/json"), HTTPTransport.FORMAT_JSON),
        (_Response({}, content_type="text/event-stream"), HTTPTransport.FORMAT_STREAMABLE_STATELESS),
        (_Response({}, status=406), HTTPTransport.FORMAT_STREAMABLE_STATELESS),
        (_Response({"error": {"message": "missing session"}}, status=400), HTTPTransport.FORMAT_STREAMABLE),
    ],
)
def test_format_detection_parity(monkeypatch, response, expected):
    transport = HTTPTransport("http://local.invalid/mcp")
    transport._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    monkeypatch.setattr(http_session.requests, "post", lambda *_a, **_k: response)
    assert transport.get_format() == expected
def test_session_initialization_preserves_header_and_sse_fallback(monkeypatch):
    transport = _transport()
    response = _Response({"result": {"protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION}})
    response.headers["Mcp-Session-Id"] = "server-session"
    monkeypatch.setattr(http_session.requests, "post", lambda *_a, **_k: response)
    assert transport._initialize_session().status is NegotiationStatus.NEGOTIATED
    assert transport._session_id == "server-session"
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (_Response({"result": {"value": 1}}), {"value": 1}),
        (_Response({"error": {"code": -1}}), {"error": {"code": -1}}),
        (_Response({"meta": 1}), {"meta": 1}),
        (_Response(error=ValueError("bad json")), None),
        (_Response(content_type="text/event-stream", lines=()), None),
        (_Response(content_type="text/event-stream", lines=(b"data: {}",)), None),
        (_Response(content_type="text/event-stream", lines=(b'data: {"result": {"value": 2}}',)), {"value": 2}),
        (_Response(content_type="text/event-stream", lines=(b'data: {"result": {"value": 1}}', b'data: {"result": {"value": 2}}')), {"value": 1}),
        (_Response(content_type="text/event-stream", lines=(b'data: {"result": {"value": 1}}', b'data: []')), None),
        (_Response(content_type="text/event-stream", lines=(b'data: {"result": {"value": 1}}', b'data: {"error": "bad"}')), None),
        (_Response(content_type="text/event-stream", lines=(b'data: {"result": {"value": 1}}', b'data: {"result": null}')), None),
    ],
)
def test_response_parse_parity(response, expected):
    observation = http_response.parse_response_outcome(response)
    if expected is None:
        assert (observation.outcome.status, observation.outcome.protocol_failure_kind) == (RequestStatus.PROTOCOL_FAILURE, FailureKind.MALFORMED_RESPONSE)
    elif "error" in expected:
        assert (observation.outcome.status, observation.outcome.protocol_failure_kind, dict(observation.outcome.protocol_error)) == (RequestStatus.PROTOCOL_FAILURE, FailureKind.JSON_RPC_ERROR, expected["error"])
    else:
        assert observation.outcome.status is RequestStatus.OK
        assert dict(observation.outcome.payload) == expected
@pytest.mark.parametrize(
    ("response", "status", "kind"),
    [
        (_Response({"result": {"value": 1}}), RequestStatus.OK, None),
        (_Response({"error": {"code": -1}}), RequestStatus.PROTOCOL_FAILURE, FailureKind.JSON_RPC_ERROR),
        (_Response({"meta": 1}), RequestStatus.OK, None),
        (_Response(error=ValueError("bad json")), RequestStatus.PROTOCOL_FAILURE, FailureKind.MALFORMED_RESPONSE),
        (_Response(content_type="text/event-stream", lines=()), RequestStatus.PROTOCOL_FAILURE, FailureKind.MALFORMED_RESPONSE),
    ],
)
def test_single_parser_produces_controlled_observations(response, status, kind):
    observation = http_response.parse_response_outcome(response)
    assert observation.outcome.status is status
    assert observation.outcome.protocol_failure_kind is kind
    assert isinstance(observation, MCPHTTPRequestObservation)
def test_typed_request_preserves_empty_legacy_transport_error(monkeypatch):
    class _BlankError(Exception):
        def __str__(self):
            return ""

    transport = _transport()
    monkeypatch.setattr(http_request.requests, "post", lambda *_a, **_k: (_ for _ in ()).throw(_BlankError()))
    observation = http_request.smart_request(transport, {})
    assert observation.outcome.status is RequestStatus.TRANSPORT_FAILURE
    assert observation.outcome.transport_diagnostic
    assert observation.transport_error_text == ""
    envelope = transport.call_tool("demo", {})
    assert isinstance(envelope, MCPToolResultEnvelope)
    assert envelope.status is ToolStatus.TRANSPORT_FAILURE
    assert envelope.transport_diagnostic
def test_retry_and_call_tool_parity(monkeypatch):
    transport = _transport()
    responses = iter([
        _Response({"error": {"message": "session expired"}}, status=400),
        _Response({"result": {"content": [{"type": "text", "text": "ok"}], "structuredContent": {"value": 1}, "isError": False}}),
    ])
    stale_states = []
    monkeypatch.setattr(http_request.requests, "post", lambda *_a, **_k: next(responses))
    monkeypatch.setattr(transport, "_initialize_session", lambda: stale_states.append((transport._session_id, transport._protocol_negotiation_result)) or setattr(transport, "_protocol_negotiation_result", validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)) or transport._protocol_negotiation_result)
    envelope = transport.call_tool("demo", {})
    assert envelope.status is ToolStatus.SUCCESS
    assert envelope.content_presence is Presence.VALUE
    assert envelope.structured_content_presence is Presence.VALUE
    assert envelope.is_error is False
    assert transport._format == transport.FORMAT_STREAMABLE
    assert stale_states == [(None, None)]
    transport.reset()
    assert transport._session_id is None and transport._protocol_negotiation_result is None
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (_Response(error=ValueError("bad json")), None),
        (_Response({"error": {"code": -7}}), {"error": {"code": -7}}),
    ],
)
def test_call_tool_preserves_malformed_and_json_rpc_error(monkeypatch, response, expected):
    transport = _transport()
    monkeypatch.setattr(http_request.requests, "post", lambda *_a, **_k: response)
    envelope = transport.call_tool("demo", {})
    assert isinstance(envelope, MCPToolResultEnvelope)
    assert envelope.status is ToolStatus.PROTOCOL_FAILURE
    assert envelope.protocol_error is None if expected is None else dict(envelope.protocol_error) == expected["error"]
def test_split_has_single_parser_and_retry_body_and_http_facade_is_small():
    assert callable(http_response.parse_response_outcome)
    assert callable(http_request.smart_request)
    assert len(Path("mcp/transports/http.py").read_text().splitlines()) < 200
