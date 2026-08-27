from dataclasses import FrozenInstanceError

import pytest

from mcp.protocol_contracts import (
    MCPSTDIOReadObservation,
    MCPSTDIOReadStatus,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_negotiation_contracts import (
    SUPPORTED_MCP_PROTOCOL_VERSION,
    MCPProtocolNegotiationResult,
    MCPProtocolNegotiationStatus as Status,
    validate_protocol_version,
)
from mcp.transports import http_request, http_session
from mcp.transports.http import HTTPTransport
from mcp.transports.stdio import STDIOTransport

class _Response:
    def __init__(self, payload, *, headers=None, status=200):
        self.payload = payload
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.status_code = status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

def _http_transport():
    transport = HTTPTransport("http://local.invalid/mcp", "secret", timeout=7)
    transport._format = transport.FORMAT_JSON
    transport._format_detected = True
    return transport

def test_protocol_version_contract_is_exact_and_fail_closed():
    assert SUPPORTED_MCP_PROTOCOL_VERSION == "2024-11-05"
    assert validate_protocol_version(None).status is Status.MISSING
    assert validate_protocol_version(20241105).status is Status.MALFORMED
    assert validate_protocol_version("").status is Status.MALFORMED
    unsupported = validate_protocol_version("2025-01-01")
    assert unsupported == MCPProtocolNegotiationResult(Status.UNSUPPORTED, "2025-01-01")
    negotiated = validate_protocol_version("2024-11-05")
    assert negotiated == MCPProtocolNegotiationResult(Status.NEGOTIATED, "2024-11-05")


def test_protocol_negotiation_result_is_immutable_and_consistent():
    result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    with pytest.raises(FrozenInstanceError):
        result.protocol_version = "changed"
    with pytest.raises(ValueError):
        MCPProtocolNegotiationResult(Status.NEGOTIATED, "2025-01-01")
    with pytest.raises(ValueError):
        MCPProtocolNegotiationResult(Status.MISSING, SUPPORTED_MCP_PROTOCOL_VERSION)
    with pytest.raises(ValueError):
        MCPProtocolNegotiationResult(Status.UNSUPPORTED, SUPPORTED_MCP_PROTOCOL_VERSION)

def test_http_negotiated_state_is_stored_and_followup_header_is_exact(monkeypatch):
    transport = _http_transport()
    initialization = _Response(
        {"result": {"protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION}},
        headers={"Mcp-Session-Id": "server-session"},
    )
    monkeypatch.setattr(http_session.requests, "post", lambda *_args, **_kwargs: initialization)
    negotiation = transport._initialize_session()
    seen = {}

    def followup_post(url, **kwargs):
        seen.update(url=url, **kwargs)
        return _Response({"result": {"tools": []}})

    monkeypatch.setattr(http_request.requests, "post", followup_post)
    observation = http_request.smart_request(transport, {"method": "tools/list"})
    assert negotiation is transport._protocol_negotiation_result
    assert transport._session_id == "server-session"
    assert observation.outcome.status is RequestStatus.OK
    assert seen["headers"] == {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer secret",
        "MCP-Protocol-Version": SUPPORTED_MCP_PROTOCOL_VERSION,
        "Mcp-Session-Id": "server-session",
    }


def test_http_session_id_without_negotiated_state_is_rejected(monkeypatch):
    transport = _http_transport()
    transport._session_id = "stale-session"
    assert transport._get_headers_with_session().status is Status.MISSING
    posts = []

    def initialize_only(*_args, **kwargs):
        posts.append(kwargs["json"]["method"])
        if posts[-1] != "initialize":
            pytest.fail("followup post must not run")
        return _Response({"result": {}})

    monkeypatch.setattr(http_session.requests, "post", initialize_only)
    observation = http_request.smart_request(transport, {})
    assert observation.outcome.status is RequestStatus.PROTOCOL_FAILURE
    assert observation.outcome.protocol_failure_kind is FailureKind.MALFORMED_RESPONSE
    assert posts == ["initialize"]
    monkeypatch.setattr(http_session.requests, "post", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("offline")))
    io_failure = http_request.smart_request(_http_transport(), {})
    assert io_failure.outcome.status is RequestStatus.TRANSPORT_FAILURE


@pytest.mark.parametrize(
    ("initialize_result", "expected_status"),
    [
        ({}, Status.MISSING),
        ({"protocolVersion": 20241105}, Status.MALFORMED),
        ({"protocolVersion": "2025-01-01"}, Status.UNSUPPORTED),
    ],
)
def test_http_invalid_protocol_versions_clear_stale_state_and_skip_followup(
    monkeypatch, initialize_result, expected_status
):
    transport = _http_transport()
    transport._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    transport._session_id = "stale-session"
    posts = []

    def initialize_only(*_args, **kwargs):
        posts.append(kwargs["json"].get("method"))
        if posts[-1] != "initialize":
            pytest.fail("followup post must not run")
        return _Response({"result": initialize_result})

    monkeypatch.setattr(http_session.requests, "post", initialize_only)
    negotiation = transport._initialize_session()
    observation = http_request.smart_request(transport, {})
    assert negotiation.status is expected_status
    assert observation.outcome.status is RequestStatus.PROTOCOL_FAILURE
    assert posts == ["initialize", "initialize"]
    assert transport._protocol_negotiation_result is None
    assert transport._session_id is None


def test_http_reinitialize_cannot_reuse_previous_negotiated_state(monkeypatch):
    transport = _http_transport()
    previous = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    transport._protocol_negotiation_result = previous
    transport._session_id = "previous-session"
    monkeypatch.setattr(http_session.requests, "post", lambda *_a, **_k: _Response({"result": {}}))
    result = transport._initialize_session()
    assert result.status is Status.MISSING
    assert transport._protocol_negotiation_result is None
    assert transport._session_id is None


def test_http_initialize_uses_base_headers_without_protocol_followup_header(monkeypatch):
    transport = _http_transport()
    transport._session_id = "stale-session"
    seen = {}

    def initialize_post(_url, **kwargs):
        seen.update(kwargs)
        return _Response({"result": {"protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION}})

    monkeypatch.setattr(http_session.requests, "post", initialize_post)
    transport._initialize_session()
    assert seen["headers"] == {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer secret",
    }
    assert seen["json"]["params"]["protocolVersion"] == SUPPORTED_MCP_PROTOCOL_VERSION
def test_stdio_initialize_notifies_only_after_exact_negotiation(monkeypatch):
    transport = STDIOTransport("ignored")
    writes = []
    monkeypatch.setattr(transport, "_write_payload", writes.append)
    monkeypatch.setattr(
        transport,
        "_wait_for_response",
        lambda _timeout: MCPSTDIOReadObservation(
            MCPSTDIOReadStatus.JSON_MESSAGE,
            payload={"result": {"protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION}},
        ),
    )
    transport._initialize_process()
    assert writes[0]["params"]["protocolVersion"] == SUPPORTED_MCP_PROTOCOL_VERSION
    assert writes[1]["method"] == "notifications/initialized"
    writes.clear()
    monkeypatch.setattr(
        transport,
        "_wait_for_response",
        lambda _timeout: MCPSTDIOReadObservation(
            MCPSTDIOReadStatus.JSON_MESSAGE,
            payload={"result": {"protocolVersion": "2025-01-01"}},
        ),
    )
    with pytest.raises(Exception, match="UNSUPPORTED"):
        transport._initialize_process()
    assert len(writes) == 1
