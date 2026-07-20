from time import monotonic
from typing import Any, Callable, Dict, Optional

from mcp.client import call_tool
from tools.contracts import ToolCall, ToolResult

CallToolFn = Callable[[str, Dict[str, Any], float], Optional[Dict[str, Any]]]


def _as_result_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"value": value}


def run_tool(tool_call: ToolCall, call_tool_fn: CallToolFn = call_tool) -> ToolResult:
    started = monotonic()
    tool_name = str(tool_call.tool_name or "").strip()

    if not tool_name:
        return ToolResult(
            tool_name=tool_name,
            step_id=tool_call.step_id,
            success=False,
            error="missing_tool_name",
            duration_s=monotonic() - started,
        )

    try:
        raw = call_tool_fn(
            tool_name,
            dict(tool_call.arguments or {}),
            max(0.2, float(tool_call.timeout_s or 0.0)),
        )
    except Exception as exc:
        return ToolResult(
            tool_name=tool_name,
            step_id=tool_call.step_id,
            success=False,
            error=str(exc),
            duration_s=monotonic() - started,
        )

    payload = _as_result_dict(raw or {})
    error = payload.get("error")
    if error:
        return ToolResult(
            tool_name=tool_name,
            step_id=tool_call.step_id,
            success=False,
            result=payload,
            error=str(error),
            duration_s=monotonic() - started,
        )

    result = payload.get("result", payload)
    return ToolResult(
        tool_name=tool_name,
        step_id=tool_call.step_id,
        success=True,
        result=_as_result_dict(result),
        duration_s=monotonic() - started,
    )
