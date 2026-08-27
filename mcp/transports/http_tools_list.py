"""Typed tools/list request for HTTP transports."""

from mcp.protocol_tools_list import project_tools_list_response
from mcp.transports.http_request import smart_request
from utils.logger import log_debug


def list_tools_protocol_result(transport):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    log_debug(f"[HTTP] tools/list → {transport.url}")
    return project_tools_list_response(smart_request(transport, payload).outcome)
