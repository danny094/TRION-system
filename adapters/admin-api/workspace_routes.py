"""
Workspace Routes — CRUD + Events via MCP Hub.
"""
import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from utils.logger import log_error

router = APIRouter()


async def _hub_call_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    from mcp.hub import get_hub
    hub = get_hub()
    hub.initialize()
    return await asyncio.to_thread(hub.call_tool, tool_name, args)


def _extract_events(result_obj) -> list:
    if isinstance(result_obj, list):
        return result_obj
    if isinstance(result_obj, dict):
        sc = result_obj.get("structuredContent", {})
        payload = (result_obj.get("events") or result_obj.get("content")
                   or (sc.get("events") if isinstance(sc, dict) else None) or [])
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = []
        return payload if isinstance(payload, list) else []
    return []


@router.get("/api/workspace")
async def workspace_list(conversation_id: str = None, limit: int = 50):
    try:
        args = {"limit": limit}
        if conversation_id:
            args["conversation_id"] = conversation_id
        result = await _hub_call_tool("workspace_list", args)
        if isinstance(result, dict):
            sc = result.get("structuredContent", result)
            entries = sc.get("entries", [])
            return JSONResponse({"entries": entries, "count": len(entries)})
        return JSONResponse({"entries": [], "count": 0})
    except Exception as e:
        log_error(f"[Workspace] List error: {e}")
        return JSONResponse({"error": str(e), "entries": [], "count": 0}, status_code=500)


@router.get("/api/workspace/{entry_id}")
async def workspace_get(entry_id: int):
    try:
        result = await _hub_call_tool("workspace_get", {"entry_id": entry_id})
        if isinstance(result, dict) and result.get("error"):
            return JSONResponse(result, status_code=404)
        return JSONResponse(result if isinstance(result, dict) else {"error": "Not found"})
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
        if isinstance(result, dict):
            sc = result.get("structuredContent", result)
            return JSONResponse({"updated": bool(sc.get("updated", sc.get("success", False)))})
        return JSONResponse({"updated": False})
    except Exception as e:
        log_error(f"[Workspace] Update error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/workspace/{entry_id}")
async def workspace_delete(entry_id: int):
    try:
        result = await _hub_call_tool("workspace_delete", {"entry_id": entry_id})
        if isinstance(result, dict):
            sc = result.get("structuredContent", result)
            return JSONResponse({"deleted": bool(sc.get("deleted", sc.get("success", False)))})
        return JSONResponse({"deleted": False})
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
