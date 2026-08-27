"""Smart HTTP MCP transport with thin split-module facades."""

from typing import Any, Dict, Optional

from mcp.protocol_contracts import MCPToolsListProtocolStatus as ListStatus
from mcp.protocol_negotiation_contracts import MCPProtocolNegotiationResult
from mcp.tool_result_contracts import MCPToolResultEnvelope, project_tool_result_envelope
from mcp.transports import http_request, http_session, http_tools_list
from utils.logger import log_debug


class HTTPTransport:
    """Auto-detecting JSON-RPC and Streamable HTTP transport."""

    FORMAT_UNKNOWN = "unknown"
    FORMAT_JSON = "json"
    FORMAT_STREAMABLE = "streamable"
    FORMAT_STREAMABLE_STATELESS = "streamable-stateless"

    def __init__(self, url: str, api_key: str = None, timeout: int = 30):
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        self._format: Optional[str] = None
        self._session_id: Optional[str] = None
        self._protocol_negotiation_result: MCPProtocolNegotiationResult | None = None
        self._format_detected = False

    def _get_base_headers(self) -> Dict[str, str]:
        return http_session.get_base_headers(self)

    def _get_headers_with_session(self) -> Dict[str, str] | MCPProtocolNegotiationResult:
        return http_session.get_headers_with_session(self)

    def _detect_format(self) -> str:
        return http_session.detect_format(self)

    def _initialize_session(self) -> MCPProtocolNegotiationResult:
        return http_session.initialize_session(self)

    def _ensure_session(self) -> MCPProtocolNegotiationResult:
        return http_session.ensure_session(self)

    def list_tools_protocol_result(self):
        return http_tools_list.list_tools_protocol_result(self)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResultEnvelope:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        log_debug(f"[HTTP] tools/call {tool_name} → {self.url}")
        observation = http_request.smart_request(self, payload)
        return project_tool_result_envelope(observation.outcome)

    def get_format(self) -> str:
        if not self._format_detected:
            self._detect_format()
        return self._format or self.FORMAT_UNKNOWN

    def shutdown(self):
        return None

    def reset(self):
        self._format = None
        self._session_id = None
        self._protocol_negotiation_result = None
        self._format_detected = False
