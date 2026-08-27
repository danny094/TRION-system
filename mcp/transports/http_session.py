"""HTTP format and canonical protocol negotiation helpers."""

from collections.abc import Mapping

import requests

from mcp.protocol_contracts import MCPTransportRequestStatus as RequestStatus
from mcp.protocol_negotiation_contracts import (
    SUPPORTED_MCP_PROTOCOL_VERSION,
    MCPProtocolNegotiationResult,
    MCPProtocolNegotiationStatus as NegotiationStatus,
    validate_protocol_version,
)
from mcp.transports.http_response import parse_response_outcome
from utils.logger import log_debug, log_error, log_info, log_warning


def get_base_headers(transport):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if transport.api_key:
        headers["Authorization"] = f"Bearer {transport.api_key}"
    return headers


def get_headers_with_session(transport):
    negotiation = transport._protocol_negotiation_result
    if not isinstance(negotiation, MCPProtocolNegotiationResult):
        return validate_protocol_version(None)
    if negotiation.status is not NegotiationStatus.NEGOTIATED:
        return negotiation
    headers = transport._get_base_headers()
    headers["MCP-Protocol-Version"] = negotiation.protocol_version
    if transport._session_id:
        headers["Mcp-Session-Id"] = transport._session_id
    return headers


def detect_format(transport):
    if transport._format_detected:
        return transport._format
    negotiation = transport._ensure_session()
    if negotiation.status is not NegotiationStatus.NEGOTIATED:
        return transport.FORMAT_UNKNOWN
    headers = transport._get_headers_with_session()
    if isinstance(headers, MCPProtocolNegotiationResult):
        return transport.FORMAT_UNKNOWN
    log_debug(f"[HTTP] Auto-detecting format for {transport.url}")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }
    try:
        response = requests.post(
            transport.url,
            json=payload,
            headers=headers,
            timeout=transport.timeout,
            stream=True,
        )
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 400:
            try:
                message = response.json().get("error", {}).get("message", "")
                if "session" in message.lower() or "Missing session ID" in message:
                    log_info("[HTTP] Detected: Streamable HTTP (needs session)")
                    transport._format = transport.FORMAT_STREAMABLE
                    transport._format_detected = True
                    return transport._format
            except Exception:
                pass
        if response.status_code == 200:
            if "text/event-stream" in content_type:
                log_info("[HTTP] Detected: Streamable HTTP (stateless)")
                transport._format = transport.FORMAT_STREAMABLE_STATELESS
            else:
                log_info("[HTTP] Detected: Simple JSON-RPC")
                transport._format = transport.FORMAT_JSON
            transport._format_detected = True
            return transport._format
        if response.status_code == 406:
            log_info("[HTTP] Detected: Streamable HTTP (stateless, needs Accept header)")
            transport._format = transport.FORMAT_STREAMABLE_STATELESS
            transport._format_detected = True
            return transport._format
        log_warning(f"[HTTP] Could not detect format, status={response.status_code}")
    except Exception as exc:
        log_error(f"[HTTP] Format detection failed: {exc}")
    transport._format = transport.FORMAT_UNKNOWN
    transport._format_detected = True
    return transport._format


def initialize_session(transport):
    transport._session_id = None
    transport._protocol_negotiation_result = None
    log_debug(f"[HTTP] Initializing session for {transport.url}")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": SUPPORTED_MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mcp-hub", "version": "1.0.0"},
        },
    }
    try:
        response = requests.post(
            transport.url,
            json=payload,
            headers=transport._get_base_headers(),
            timeout=transport.timeout,
            stream=True,
        )
        response.raise_for_status()
        outcome = parse_response_outcome(response).outcome
        payload = outcome.payload if outcome.status is RequestStatus.OK else {}
        protocol_value = payload.get("protocolVersion") if isinstance(payload, Mapping) else {}
        negotiation = validate_protocol_version(protocol_value)
        if negotiation.status is NegotiationStatus.NEGOTIATED:
            transport._protocol_negotiation_result = negotiation
            transport._session_id = response.headers.get("Mcp-Session-Id")
            if transport._session_id:
                log_info(f"[HTTP] Session initialized: {transport._session_id[:8]}...")
        return negotiation
    except Exception as exc:
        log_error(f"[HTTP] Session initialization failed: {exc}")
        raise


def ensure_session(transport):
    negotiation = transport._protocol_negotiation_result
    if (
        isinstance(negotiation, MCPProtocolNegotiationResult)
        and negotiation.status is NegotiationStatus.NEGOTIATED
    ):
        return negotiation
    return transport._initialize_session()
