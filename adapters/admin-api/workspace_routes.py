"""
Workspace Routes — CRUD + Events via MCP Hub.
"""
import asyncio
import json
from collections.abc import Mapping
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)
from utils.logger import log_error

router = APIRouter()


async def _hub_call_tool(
    tool_name: str,
    args: Dict[str, Any],
) -> MCPToolResultEnvelope:
    from mcp.hub import get_hub
    hub = get_hub()
    hub.initialize()
    return await asyncio.to_thread(hub.call_tool, tool_name, args)


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _structured_result(result: MCPToolResultEnvelope) -> dict:
    if not isinstance(result, MCPToolResultEnvelope):
        raise TypeError("tool result must be MCPToolResultEnvelope")
    if result.status is not MCPToolCallStatus.SUCCESS:
        raise RuntimeError(f"tool call failed: {result.status.name}")
    if result.structured_content_presence is MCPResultPresence.MISSING:
        return {}
    return _json_value(result.structured_content)


def _extract_events(result: MCPToolResultEnvelope) -> list:
    structured = _structured_result(result)
    payload = structured.get("events")
    if payload is None and result.content_presence is not MCPResultPresence.MISSING:
        payload = _json_value(result.content)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            return []
    return payload if isinstance(payload, list) else []


@router.get("/api/workspace")
async def workspace_list(conversation_id: str = None, limit: int = 50):
    try:
        args = {"limit": limit}
        if conversation_id:
            args["conversation_id"] = conversation_id
        result = await _hub_call_tool("workspace_list", args)
        entries = _structured_result(result).get("entries", [])
        return JSONResponse({"entries": entries, "count": len(entries)})
    except Exception as e:
        log_error(f"[Workspace] List error: {e}")
        return JSONResponse({"error": str(e), "entries": [], "count": 0}, status_code=500)


@router.get("/api/workspace/{entry_id}")
async def workspace_get(entry_id: int):
    try:
        result = await _hub_call_tool("workspace_get", {"entry_id": entry_id})
        return JSONResponse(_structured_result(result))
    except Exception as e:
        log_error(f"[Workspace] Get error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/workspace/{entry_id}")
async def workspace_update(entry_id: int, request: Request):
    try:
        data = await request.json()
        content = data.get("content", "")
        if not content:
            return JSONResponse({"error": "content is required"}, status_code=400)
        result = await _hub_call_tool("workspace_update", {"entry_id": entry_id, "content": content})
        structured = _structured_result(result)
        return JSONResponse({"updated": bool(structured.get("updated", structured.get("success", False)))})
    except Exception as e:
        log_error(f"[Workspace] Update error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/workspace/{entry_id}")
async def workspace_delete(entry_id: int):
    try:
        result = await _hub_call_tool("workspace_delete", {"entry_id": entry_id})
        structured = _structured_result(result)
        return JSONResponse({"deleted": bool(structured.get("deleted", structured.get("success", False)))})
    except Exception as e:
        log_error(f"[Workspace] Delete error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/workspace-events")
async def workspace_events_list(conversation_id: str = None, event_type: str = None, limit: int = 50):
    try:
        args: dict = {"limit": limit}
        if conversation_id:
            args["conversation_id"] = conversation_id
        if event_type:
            args["event_type"] = event_type
        result = await _hub_call_tool("workspace_event_list", args)
        events = _extract_events(result)
        return JSONResponse({"events": events, "count": len(events)})
    except Exception as e:
        log_error(f"[WorkspaceEvents] List error: {e}")
        return JSONResponse({"error": str(e), "events": [], "count": 0}, status_code=500)
