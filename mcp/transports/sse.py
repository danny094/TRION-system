# mcp/transports/sse.py
"""
SSE (Server-Sent Events) Transport für MCPs.
Für Streaming/Realtime MCPs.
"""

import requests
from collections.abc import Mapping
from typing import Dict, Any, List, Generator
from mcp.protocol_contracts import (
    MCPToolsListProtocolResult,
    MCPToolsListProtocolStatus as ListStatus,
    MCPTransportProtocolFailureKind as FailureKind,
    MCPTransportRequestOutcome,
    MCPTransportRequestStatus as RequestStatus,
)
from mcp.protocol_negotiation_contracts import (
    MCPProtocolNegotiationResult,
    MCPProtocolNegotiationStatus as NegotiationStatus,
)
from mcp.tool_result_contracts import MCPToolResultEnvelope, project_tool_result_envelope
from mcp.transports import sse_request, sse_response, sse_tools_list
from utils.logger import log_info, log_error, log_debug


class SSETransport:
    """SSE Transport für Streaming MCPs."""
    
    def __init__(self, url: str, api_key: str = None, timeout: int = 60):
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self._protocol_negotiation_result: MCPProtocolNegotiationResult | None = None

    def _ensure_protocol_negotiated(self) -> MCPProtocolNegotiationResult:
        if self._protocol_negotiation_result is None:
            self._protocol_negotiation_result = sse_request.initialize_sse_protocol(self)
        return self._protocol_negotiation_result
    
    def _get_headers(self) -> Dict[str, str]:
        """Baut HTTP Headers."""
        return sse_request.build_sse_headers(
            self.api_key,
            accept_event_stream=True,
            protocol_negotiation_result=self._protocol_negotiation_result,
        )
    
    def _extract_mcp_content(self, result: Any) -> Any:
        """
        Extrahiert Content aus MCP Protocol Format.
        
        FastMCP Format: {"content": [{"type": "text", "text": "JSON_STRING"}]}
        Diese Funktion extrahiert und parst den JSON-String.
        """
        return sse_response.decode_sse_tool_result_envelope(result)

    
    def list_tools_protocol_result(self):
        try:
            negotiation = self._ensure_protocol_negotiated()
        except Exception as exc:
            log_error(f"[SSE] Protocol initialization failed: {exc}")
            return MCPToolsListProtocolResult(ListStatus.TRANSPORT_FAILURE)
        if negotiation.status is not NegotiationStatus.NEGOTIATED:
            return MCPToolsListProtocolResult(ListStatus.PROTOCOL_FAILURE)
        return sse_tools_list.list_tools_protocol_result(self)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResultEnvelope:
        """Ruft ein Tool auf (sammelt alle SSE Events)."""
        try:
            negotiation = self._ensure_protocol_negotiated()
            if negotiation.status is not NegotiationStatus.NEGOTIATED:
                outcome = MCPTransportRequestOutcome(
                    RequestStatus.PROTOCOL_FAILURE,
                    protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
                )
                return project_tool_result_envelope(outcome)
            payload = sse_request.build_sse_tool_call_payload(tool_name, arguments)
            
            log_debug(f"[SSE] tools/call {tool_name} → {self.url}")
            
            outcome = None
            
            with requests.post(
                self.url,
                json=payload,
                headers=self._get_headers(),
                stream=True,
                timeout=self.timeout
            ) as resp:
                resp.raise_for_status()
                
                for line in resp.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        
                        if line.startswith("data: "):
                            data = sse_response.decode_sse_event(line)
                            if data is None:
                                continue
                            if not isinstance(data, Mapping):
                                outcome = MCPTransportRequestOutcome(
                                    RequestStatus.PROTOCOL_FAILURE,
                                    protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
                                )
                                break
                            if "error" in data:
                                if isinstance(data["error"], Mapping):
                                    outcome = MCPTransportRequestOutcome(
                                        RequestStatus.PROTOCOL_FAILURE,
                                        protocol_failure_kind=FailureKind.JSON_RPC_ERROR,
                                        protocol_error=data["error"],
                                    )
                                else:
                                    outcome = MCPTransportRequestOutcome(
                                        RequestStatus.PROTOCOL_FAILURE,
                                        protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
                                    )
                                break
                            if "result" in data:
                                candidate = sse_response.decode_sse_tool_result_envelope(data["result"])
                                if candidate.status is RequestStatus.PROTOCOL_FAILURE:
                                    outcome = candidate
                                    break
                                if outcome is None:
                                    outcome = candidate
            if outcome is None:
                outcome = MCPTransportRequestOutcome(
                    RequestStatus.PROTOCOL_FAILURE,
                    protocol_failure_kind=FailureKind.MALFORMED_RESPONSE,
                )
            return project_tool_result_envelope(outcome)
            
        except Exception as exc:
            diagnostic = str(exc) or "SSE transport failure"
            log_error(f"[SSE] call_tool failed: {exc}")
            return project_tool_result_envelope(MCPTransportRequestOutcome(
                RequestStatus.TRANSPORT_FAILURE,
                transport_diagnostic=diagnostic,
            ))
    
    def call_tool_stream(self, tool_name: str, arguments: Dict[str, Any]) -> Generator[Dict, None, None]:
        """Ruft ein Tool auf und streamt Events."""
        try:
            negotiation = self._ensure_protocol_negotiated()
            if negotiation.status is not NegotiationStatus.NEGOTIATED:
                yield {"error": "MCP protocol negotiation failed"}
                return
            payload = sse_request.build_sse_tool_call_payload(tool_name, arguments)
            
            log_debug(f"[SSE] tools/call (stream) {tool_name} → {self.url}")
            
            with requests.post(
                self.url,
                json=payload,
                headers=self._get_headers(),
                stream=True,
                timeout=self.timeout
            ) as resp:
                resp.raise_for_status()
                
                for line in resp.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        
                        if line.startswith("data: "):
                            data = sse_response.decode_sse_event(line)
                            if data is not None:
                                yield data
                                
        except Exception as e:
            log_error(f"[SSE] call_tool_stream failed: {e}")
            yield {"error": str(e)}
    
    def shutdown(self):
        return None
