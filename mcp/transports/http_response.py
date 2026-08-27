"""Behavior-preserving HTTP response parsing helpers."""

import json

from mcp.protocol_contracts import (
    MCPHTTPRequestObservation,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
def parse_response_outcome(response):
    def malformed():
        return MCPHTTPRequestObservation(MCPTransportRequestOutcome(
            RequestStatus.PROTOCOL_FAILURE,
            protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
        ))

    def success(payload):
        return malformed() if payload is None else MCPHTTPRequestObservation(
            MCPTransportRequestOutcome(RequestStatus.OK, payload=payload)
        )

    def protocol_error(error):
        if not isinstance(error, dict):
            return malformed()
        return MCPHTTPRequestObservation(MCPTransportRequestOutcome(
            RequestStatus.PROTOCOL_FAILURE,
            protocol_failure_kind=FailureKind.JSON_RPC_ERROR,
            protocol_error=error,
        ))

    if "text/event-stream" in response.headers.get("Content-Type", ""):
        result = None
        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            raw = decoded[6:] if decoded.startswith("data: ") else decoded if decoded.startswith("{") else None
            if raw is None:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                return malformed()
            if "error" in data:
                return protocol_error(data["error"])
            if "result" in data:
                candidate = data["result"]
                if not isinstance(candidate, dict):
                    return malformed()
                if result is None:
                    result = candidate
        return success(result)
    try:
        data = response.json()
    except Exception:
        return malformed()
    if not isinstance(data, dict):
        return malformed()
    if "error" in data:
        return protocol_error(data["error"])
    payload = data["result"] if "result" in data else data
    return success(payload)
