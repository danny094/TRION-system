"""Current Hub-to-client handoff isolated for later typed migration."""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Dict

from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope
from utils.logger import log_error


_MAX_WORKERS = max(4, min(64, int(os.getenv("MCP_CLIENT_MAX_WORKERS", "16"))))
_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="mcp-client")


def get_hub():
    from mcp.hub import get_hub as load_hub

    return load_hub()


def call_tool_result(
    name: str,
    arguments: Dict[str, Any],
    timeout: float = 5.0,
) -> MCPToolResultEnvelope:
    try:
        future = _EXECUTOR.submit(get_hub().call_tool, name, arguments)
        result = future.result(timeout=max(0.2, float(timeout)))
        if not isinstance(result, MCPToolResultEnvelope):
            raise TypeError("hub returned a non-canonical tool result")
        return result
    except FuturesTimeout:
        log_error(f"[MCPClient] Timeout: tool={name} timeout={timeout}s")
        return MCPToolResultEnvelope(
            MCPToolCallStatus.TRANSPORT_FAILURE,
            transport_diagnostic=f"mcp_timeout:{name}:{timeout}s",
        )
    except Exception as exc:
        log_error(f"[MCPClient] call_tool failed: {exc}")
        return MCPToolResultEnvelope(
            MCPToolCallStatus.TRANSPORT_FAILURE,
            transport_diagnostic=str(exc) or "MCP client handoff failure",
        )
