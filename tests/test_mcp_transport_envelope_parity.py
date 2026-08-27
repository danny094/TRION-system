from dataclasses import FrozenInstanceError

import pytest

from mcp.protocol_contracts import (
    MCPToolsListProtocolStatus as ListStatus,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_negotiation_contracts import SUPPORTED_MCP_PROTOCOL_VERSION, validate_protocol_version
from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
    project_tool_result_envelope,
    project_tool_result_wire_mapping,
)
from mcp.transports import http_session, sse, sse_request, sse_response, sse_tools_list
from mcp.transports.http import HTTPTransport
from mcp.transports.sse import SSETransport
def _ok(payload):
    return MCPTransportRequestOutcome(RequestStatus.OK, payload=payload)
@pytest.mark.parametrize(
    ("payload", "content_presence", "structured_presence", "is_error"),
    [
        ({}, Presence.MISSING, Presence.MISSING, None),
        ({"content": [], "structuredContent": {}}, Presence.EMPTY, Presence.EMPTY, None),
        (
            {"content": [{"type": "text", "text": "ok"}], "structuredContent": {"x": 1}},
            Presence.VALUE,
            Presence.VALUE,
            None,
        ),
        ({"isError": False}, Presence.MISSING, Presence.MISSING, False),
    ],
)
def test_tool_result_projection_preserves_s1_presence(payload, content_presence, structured_presence, is_error):
    envelope = project_tool_result_envelope(_ok(payload))
    assert envelope.status is ToolStatus.SUCCESS
    assert envelope.content_presence is content_presence
    assert envelope.structured_content_presence is structured_presence
    assert envelope.is_error is is_error
    assert dict(project_tool_result_wire_mapping(envelope)) == payload
def test_tool_failure_and_failure_classes_are_contract_owned():
    tool_failure = project_tool_result_envelope(_ok({"isError": True, "content": []}))
    protocol_failure = project_tool_result_envelope(
        MCPTransportRequestOutcome(RequestStatus.PROTOCOL_FAILURE,
            protocol_failure_kind=FailureKind.JSON_RPC_ERROR,
            protocol_error={"code": -1, "data": {"retry": False}})
    )
    transport_failure = project_tool_result_envelope(
        MCPTransportRequestOutcome(RequestStatus.TRANSPORT_FAILURE, transport_diagnostic="offline")
    )
    assert tool_failure.status is ToolStatus.TOOL_FAILURE
    assert dict(project_tool_result_wire_mapping(protocol_failure))["error"]["code"] == -1
    assert transport_failure.status is ToolStatus.TRANSPORT_FAILURE
def test_tool_result_envelope_is_recursively_immutable_and_fail_closed():
    envelope = project_tool_result_envelope(
        _ok({"content": [{"data": {"value": 1}}], "structuredContent": {"items": [1]}})
    )
    with pytest.raises(FrozenInstanceError):
        envelope.status = ToolStatus.PROTOCOL_FAILURE
    with pytest.raises(TypeError):
        envelope.structured_content["items"] = []
    with pytest.raises(TypeError):
        envelope.content[0]["data"]["value"] = 2
    with pytest.raises(ValueError):
        MCPToolResultEnvelope(ToolStatus.SUCCESS, is_error_presence=Presence.EMPTY)
def test_tool_result_envelope_rejects_unknown_mutable_leaf():
    class MutableLeaf:
        pass

    with pytest.raises(TypeError, match="recursively JSON-compatible"):
        project_tool_result_envelope(_ok({"structuredContent": {"leaf": MutableLeaf()}}))
def test_sse_request_and_response_split_preserves_current_values():
    assert sse_request.build_sse_initialize_payload()["params"]["protocolVersion"] == SUPPORTED_MCP_PROTOCOL_VERSION
    assert hasattr(sse_request, "initialize_sse_protocol")
    assert sse_request.build_sse_tool_call_payload("demo", {"x": 1}) == {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "demo", "arguments": {"x": 1}},
    }
    assert sse_request.build_sse_headers("secret", True) == {
        "Content-Type": "application/json", "Accept": "text/event-stream",
        "Authorization": "Bearer secret",
    }
    assert sse_response.decode_sse_event('data: {"result": {"x": 1}}') == {
        "result": {"x": 1}
    }
    result = {"content": [{"type": "text", "text": '{"x": 1}'}]}
    outcome = sse_response.decode_sse_tool_result_envelope(result)
    assert outcome.status is RequestStatus.OK
    assert [dict(item) for item in outcome.payload["content"]] == result["content"]
    with pytest.raises(TypeError): outcome.payload["content"][0]["text"] = "changed"

def test_http_detect_format_uses_negotiation_gate_before_probe(monkeypatch):
    transport = HTTPTransport("http://local.invalid/mcp")
    calls = []

    class Response:
        headers = {"Content-Type": "application/json"}
        def json(self): return {"result": {}}
        def raise_for_status(self): return None

    monkeypatch.setattr(
        http_session.requests,
        "post",
        lambda *_args, **_kwargs: calls.append("initialize") or Response(),
    )
    assert transport.get_format() == transport.FORMAT_UNKNOWN
    assert calls == ["initialize"]


def test_sse_facade_preserves_full_result_envelope(monkeypatch):
    seen = {}

    class Response:
        def json(self): return {"result": {"protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION}}
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def raise_for_status(self): return None

        def iter_lines(self):
            return [
                b'data: {"result": {"content": [{"type": "text", "text": "ok"}], '
                b'"structuredContent": {"x": 1}, "isError": false}}'
            ]

    initialize_seen = {}

    def fake_post(url, **kwargs):
        target = initialize_seen if kwargs["json"]["method"] == "initialize" else seen
        target.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(sse.requests, "post", fake_post)
    transport = SSETransport("http://example.invalid", api_key="secret", timeout=7)
    envelope = transport.call_tool("demo", {"value": 2})
    assert envelope.status is ToolStatus.SUCCESS
    assert envelope.content[0]["text"] == "ok"
    assert envelope.structured_content["x"] == 1
    assert envelope.is_error is False
    assert "MCP-Protocol-Version" not in initialize_seen["headers"]
    assert seen == {
        "url": "http://example.invalid",
        "json": sse_request.build_sse_tool_call_payload("demo", {"value": 2}),
        "headers": sse_request.build_sse_headers("secret", True,
            validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)),
        "stream": True, "timeout": 7,
    }
    list_seen = {}
    monkeypatch.setattr(
        sse_tools_list.requests,
        "post",
        lambda url, **kwargs: list_seen.update(url=url, **kwargs) or Response(),
    )
    assert transport.list_tools_protocol_result().status is ListStatus.PROTOCOL_FAILURE
    assert list_seen["headers"]["Authorization"] == "Bearer secret"
    assert list_seen["headers"]["MCP-Protocol-Version"] == SUPPORTED_MCP_PROTOCOL_VERSION


@pytest.mark.parametrize(
    ("lines", "status", "protocol_error", "content_text"),
    [
        ([b'data: {"error": {"code": -1}}', b'data: {"result": {}}'], ToolStatus.PROTOCOL_FAILURE, {"code": -1}, None),
        ([b'data: {"error": "bad"}'], ToolStatus.PROTOCOL_FAILURE, None, None),
        ([b'data: {"result": null}'], ToolStatus.PROTOCOL_FAILURE, None, None),
        ([b'data: []'], ToolStatus.PROTOCOL_FAILURE, None, None),
        ([b'data: {"result": {}}', b'data: {"method": "notifications/progress"}'], ToolStatus.SUCCESS, None, None),
        ([b'data: {"result": {"content": [{"type": "text", "text": "first"}]}}', b'data: {"result": null}'], ToolStatus.PROTOCOL_FAILURE, None, None),
        ([b'data: {"result": {"content": [{"type": "text", "text": "first"}]}}', b'data: {"result": {"content": [{"type": "text", "text": "second"}]}}'], ToolStatus.SUCCESS, None, "first"),
    ],
)
def test_sse_event_order_preserves_typed_authority(monkeypatch, lines, status, protocol_error, content_text):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def raise_for_status(self): return None
        def iter_lines(self): return lines

    transport = SSETransport("http://example.invalid")
    transport._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    monkeypatch.setattr(sse.requests, "post", lambda *_a, **_k: Response())
    envelope = transport.call_tool("demo", {})
    assert envelope.status is status
    assert envelope.protocol_error is None if protocol_error is None else dict(envelope.protocol_error) == protocol_error
    if content_text is not None: assert envelope.content[0]["text"] == content_text

def test_sse_transport_and_negotiation_failures_stay_separate(monkeypatch):
    transport = SSETransport("http://example.invalid")
    transport._protocol_negotiation_result = validate_protocol_version(SUPPORTED_MCP_PROTOCOL_VERSION)
    monkeypatch.setattr(sse.requests, "post", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("offline")))
    failure = transport.call_tool("demo", {})
    assert failure.status is ToolStatus.TRANSPORT_FAILURE
    assert failure.transport_diagnostic == "offline"
    transport._protocol_negotiation_result = validate_protocol_version(None)
    monkeypatch.setattr(sse_tools_list, "list_tools_protocol_result", lambda _transport: pytest.fail("followup"))
    assert transport.list_tools_protocol_result().status is ListStatus.PROTOCOL_FAILURE
    assert transport.call_tool("demo", {}).status is ToolStatus.PROTOCOL_FAILURE
    assert "error" in next(transport.call_tool_stream("demo", {}))
