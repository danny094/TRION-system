"""WebUI Memory-Routen via live-discovered SQL-Memory-MCP-Tools.

Der aeltere ``trion_memory_routes.py``-Home-/Note-Pfad bleibt separat.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from core.conversation_meta.defaults import build_conversation_meta, build_default_conversation_meta
from core.conversation_meta.policy import build_effective_policy
from mcp.client import call_tool, get_conversation_meta
from memory_route_contracts import (
    DeleteBulkRequest,
    SearchRequest,
    _badge_from_policy,
    _policy_response as _build_policy_response,
)
from mcp.tool_result_contracts import MCPResultPresence, MCPToolCallStatus, MCPToolResultEnvelope
from utils.logger import log_error

router = APIRouter()

_DEFAULT_TIMEOUT_S = 5.0


def _policy_response(conversation_id: str, raw_meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return _build_policy_response(
        conversation_id,
        raw_meta,
        build_conversation_meta,
        build_default_conversation_meta,
        build_effective_policy,
    )


def _mcp_error(result: Any) -> Optional[str]:
    if not isinstance(result, MCPToolResultEnvelope):
        return "invalid_tool_result"
    if result.status is MCPToolCallStatus.SUCCESS:
        return None
    return result.status.name.lower()


def _entries_from_result(result: MCPToolResultEnvelope) -> list[dict[str, Any]]:
    if result.structured_content_presence is MCPResultPresence.MISSING:
        return []
    structured = jsonable_encoder(result.structured_content)
    for key in ("entries", "results", "items", "conversations"):
        entries = structured.get(key) if isinstance(structured, dict) else None
        if isinstance(entries, list):
            return [item for item in entries if isinstance(item, dict)]
    return []


@router.get("/api/memory/recent")
async def memory_recent(conversation_id: Optional[str] = None, limit: int = 20):
    """Liefert die juengsten Memory-Eintraege.

    Wenn ``conversation_id`` gesetzt ist, wird ``memory_recent`` (reicherer
    Contract mit role/tags/layer) genutzt. Ohne ``conversation_id`` faellt der
    Endpunkt auf ``memory_all_recent`` zurueck (duenner Contract, nur id /
    conversation_id / content / created_at).
    """
    capped_limit = max(1, min(int(limit or 20), 100))
    if conversation_id:
        payload = call_tool(
            "memory_recent",
            {"conversation_id": str(conversation_id), "limit": capped_limit},
            timeout=_DEFAULT_TIMEOUT_S,
        )
    else:
        payload = call_tool(
            "memory_all_recent",
            {"limit": capped_limit},
            timeout=_DEFAULT_TIMEOUT_S,
        )
    error = _mcp_error(payload)
    if error:
        log_error(f"[MemoryRoutes] recent failed: {error}")
        return JSONResponse({"error": error}, status_code=503)
    entries = _entries_from_result(payload)
    return JSONResponse({"entries": entries, "count": len(entries), "limit": capped_limit})


@router.post("/api/memory/search")
async def memory_search(request: SearchRequest):
    """Sucht im Memory. Drei Modi, je eigener MCP-Tool-Pfad.

    - ``fts``: ``memory_search_fts`` (volltext, schnell, breit)
    - ``semantic``: ``memory_semantic_search`` (Embedding-basiert)
    - ``graph``: ``memory_graph_search`` (graph-walk auf verknuepften Knoten)
    """
    query = (request.query or "").strip()
    if not query:
        return JSONResponse({"error": "empty_query"}, status_code=400)
    mode = (request.mode or "fts").strip().lower()
    capped_limit = max(1, min(int(request.limit or 10), 50))

    tool_name_by_mode = {
        "fts": "memory_search_fts",
        "semantic": "memory_semantic_search",
        "graph": "memory_graph_search",
    }
    tool_name = tool_name_by_mode.get(mode)
    if not tool_name:
        return JSONResponse({"error": f"unknown_mode:{mode}"}, status_code=400)

    args: Dict[str, Any] = {"query": query, "limit": capped_limit}
    if request.conversation_id:
        args["conversation_id"] = str(request.conversation_id)
    payload = call_tool(tool_name, args, timeout=_DEFAULT_TIMEOUT_S)
    error = _mcp_error(payload)
    if error:
        log_error(f"[MemoryRoutes] search failed mode={mode}: {error}")
        return JSONResponse({"error": error}, status_code=503)
    raw_hits = _entries_from_result(payload)
    hits = [{**hit, "source": mode} for hit in raw_hits]
    return JSONResponse({"mode": mode, "query": query, "hits": hits, "count": len(hits)})


@router.get("/api/memory/conversations")
async def memory_conversations(limit: int = 50):
    capped_limit = max(1, min(int(limit or 50), 200))
    payload = call_tool(
        "memory_list_conversations",
        {"limit": capped_limit},
        timeout=_DEFAULT_TIMEOUT_S,
    )
    error = _mcp_error(payload)
    if error:
        log_error(f"[MemoryRoutes] list_conversations failed: {error}")
        return JSONResponse({"error": error}, status_code=503)
    entries = _entries_from_result(payload)
    return JSONResponse({"conversations": entries, "count": len(entries)})


@router.get("/api/memory/conversations/{conversation_id}")
async def memory_conversation_drill_in(conversation_id: str, limit: int = 50):
    capped_limit = max(1, min(int(limit or 50), 200))
    payload = call_tool(
        "memory_recent",
        {"conversation_id": str(conversation_id), "limit": capped_limit},
        timeout=_DEFAULT_TIMEOUT_S,
    )
    error = _mcp_error(payload)
    if error:
        log_error(f"[MemoryRoutes] drill-in failed: {error}")
        return JSONResponse({"error": error}, status_code=503)
    entries = _entries_from_result(payload)
    return JSONResponse({"conversation_id": conversation_id, "entries": entries, "count": len(entries)})


@router.get("/api/memory/conversations/{conversation_id}/policy")
async def memory_conversation_policy(conversation_id: str):
    """UI-freundlich normalisierte Policy.

    Felder sind direkt fuer Anzeige und Badge nutzbar. Quelle: existierender
    ``conversation_meta_get``-Helper. Wenn keine Meta existiert, wird der
    System-Default zurueckgegeben (``memory_mode=global_enabled``).
    """
    raw_meta = get_conversation_meta(str(conversation_id))
    return JSONResponse(_policy_response(conversation_id, raw_meta))


@router.delete("/api/memory/{memory_id}")
async def memory_delete(memory_id: int):
    if memory_id <= 0:
        raise HTTPException(status_code=400, detail="invalid_memory_id")
    payload = call_tool(
        "memory_delete",
        {"id": int(memory_id)},
        timeout=_DEFAULT_TIMEOUT_S,
    )
    error = _mcp_error(payload)
    if error:
        log_error(f"[MemoryRoutes] delete failed id={memory_id}: {error}")
        return JSONResponse({"ok": False, "error": error}, status_code=503)
    return JSONResponse({"ok": True, "deleted_count": 1})


@router.post("/api/memory/delete-bulk")
async def memory_delete_bulk(request: DeleteBulkRequest):
    ids = [int(value) for value in (request.ids or []) if isinstance(value, int) or (isinstance(value, str) and value.isdigit())]
    ids = [value for value in ids if value > 0]
    if not ids:
        return JSONResponse({"ok": False, "error": "empty_ids"}, status_code=400)
    payload = call_tool(
        "memory_delete_bulk",
        {"ids": ids},
        timeout=_DEFAULT_TIMEOUT_S,
    )
    error = _mcp_error(payload)
    if error:
        log_error(f"[MemoryRoutes] delete_bulk failed count={len(ids)}: {error}")
        return JSONResponse({"ok": False, "error": error}, status_code=503)
    return JSONResponse({"ok": True, "deleted_count": len(ids)})
