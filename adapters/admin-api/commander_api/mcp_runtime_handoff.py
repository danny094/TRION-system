from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)

_DEFAULT_TIMEOUT_S = 5.0

ERROR_STATUS = {
    "CONTAINER_NOT_FOUND": 404,
    "VOLUME_NOT_FOUND": 404,
    "ACTION_NOT_ALLOWED": 409,
    "RUNTIME_UNAVAILABLE": 503,
}


def unwrap_tool_result(tool_name: str, result: Any) -> dict[str, Any]:
    if not isinstance(result, MCPToolResultEnvelope):
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    if result.status is not MCPToolCallStatus.SUCCESS:
        error = None
        if (
            result.status is MCPToolCallStatus.TOOL_FAILURE
            and result.structured_content_presence is MCPResultPresence.VALUE
        ):
            error = result.structured_content.get("error")
        error = error if isinstance(error, Mapping) else {}
        code = str(error.get("code") or "").strip() or "commander_error"
        message = str(error.get("message") or code).strip() or code
        status_code = 503 if result.status is MCPToolCallStatus.TRANSPORT_FAILURE else ERROR_STATUS.get(code, 502)
        raise HTTPException(status_code=status_code, detail=message)
    if result.structured_content_presence is MCPResultPresence.MISSING:
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    payload = jsonable_encoder(result.structured_content)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    return payload


def call_commander_runtime_tool(
    call_tool: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    result = call_tool(tool_name, arguments or {}, timeout=timeout)
    return unwrap_tool_result(tool_name, result)
