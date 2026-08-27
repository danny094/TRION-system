"""Behavior-preserving HTTP request and retry helper."""

import requests

from mcp.protocol_contracts import (
    MCPHTTPRequestObservation,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_negotiation_contracts import (
    MCPProtocolNegotiationResult,
    MCPProtocolNegotiationStatus as NegotiationStatus,
)
from mcp.transports.http_response import parse_response_outcome
from utils.logger import log_error, log_warning


def smart_request(transport, payload, retry_count=0):
    def transport_failure(error_text):
        return MCPHTTPRequestObservation(
            MCPTransportRequestOutcome(
                RequestStatus.TRANSPORT_FAILURE,
                transport_diagnostic=error_text or "HTTP transport failure",
            ),
            error_text,
        )

    def protocol_failure():
        return MCPHTTPRequestObservation(MCPTransportRequestOutcome(
            RequestStatus.PROTOCOL_FAILURE,
            protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
        ))

    try:
        negotiation = transport._ensure_session()
        if negotiation.status is not NegotiationStatus.NEGOTIATED:
            log_error("[HTTP] Protocol negotiation rejected")
            return protocol_failure()
        if not transport._format_detected:
            transport._detect_format()
        headers = transport._get_headers_with_session()
        if isinstance(headers, MCPProtocolNegotiationResult):
            return protocol_failure()
        response = requests.post(
            transport.url,
            json=payload,
            headers=headers,
            timeout=transport.timeout,
            stream=True,
        )
        if response.status_code == 400 and retry_count < 2:
            try:
                message = response.json().get("error", {}).get("message", "")
                if "session" in message.lower():
                    log_warning("[HTTP] Session error, reinitializing...")
                    transport._session_id = None
                    transport._protocol_negotiation_result = None
                    transport._format = transport.FORMAT_STREAMABLE
                    return smart_request(transport, payload, retry_count + 1)
            except Exception:
                pass
        response.raise_for_status()
        return parse_response_outcome(response)
    except requests.exceptions.HTTPError as exc:
        log_error(f"[HTTP] HTTP error: {exc}")
        return transport_failure(str(exc))
    except Exception as exc:
        log_error(f"[HTTP] Request failed: {exc}")
        return transport_failure(str(exc))
