"""Typed tools/list request for the standalone SSE transport."""

from collections.abc import Mapping

import requests

from mcp.protocol_contracts import (
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_tools_list import project_tools_list_response
from mcp.transports import sse_request
from utils.logger import log_debug, log_error


def list_tools_protocol_result(transport):
    def malformed():
        return MCPTransportRequestOutcome(
            RequestStatus.PROTOCOL_FAILURE,
            protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
        )

    payload = sse_request.build_sse_tools_list_payload()
    log_debug(f"[SSE] tools/list → {transport.url}")
    try:
        response = requests.post(
            transport.url,
            json=payload,
            headers=sse_request.build_sse_headers(
                transport.api_key,
                protocol_negotiation_result=transport._protocol_negotiation_result,
            ),
            timeout=transport.timeout,
        )
        response.raise_for_status()
    except Exception as exc:
        text = str(exc)
        log_error(f"[SSE] tools/list failed: {exc}")
        outcome = MCPTransportRequestOutcome(
            RequestStatus.TRANSPORT_FAILURE,
            transport_diagnostic=text or "SSE transport failure",
        )
        return project_tools_list_response(outcome)
    try:
        data = response.json()
    except Exception:
        return project_tools_list_response(malformed())
    if not isinstance(data, Mapping):
        outcome = malformed()
    elif "error" in data:
        error = data["error"]
        outcome = (
            MCPTransportRequestOutcome(
                RequestStatus.PROTOCOL_FAILURE,
                protocol_failure_kind=FailureKind.JSON_RPC_ERROR,
                protocol_error=error,
            )
            if isinstance(error, Mapping)
            else malformed()
        )
    elif data.get("result") is not None:
        outcome = MCPTransportRequestOutcome(RequestStatus.OK, payload=data["result"])
    else:
        outcome = malformed()
    return project_tools_list_response(outcome)
