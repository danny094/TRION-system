"""
Memory Routes — Admin-API-Schicht fuer die WebUI Memory-App.

Stabile, UI-freundliche Endpunkte unter ``/api/memory/*``. Intern werden die
existierenden SQL-Memory-MCP-Tools via ``mcp/client.py`` aufgerufen — keine
hartcodierten Tool-Listen, keine Tool-Existenz-Behauptung ausserhalb der
Live-Discovery (siehe docs/memory-grounding/34-semantic-tool-truth-drift.md, docs/governance/36-lifecycle-rules.md
Regel 2).

Scope-Abgrenzung:
- diese Datei deckt die WebUI Memory-App ab
- ``trion_memory_routes.py`` ist ein separater aelterer Home-/Note-Pfad an
  ``container_commander`` (Root-Pfade /recent, /recall, /remember, /status) und
  wird hier bewusst nicht ersetzt
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.conversation_meta.defaults import build_conversation_meta, build_default_conversation_meta
from core.conversation_meta.policy import build_effective_policy
from mcp.client import call_tool, get_conversation_meta
from utils.logger import log_error

router = APIRouter()

_DEFAULT_TIMEOUT_S = 5.0


# ── Request Models ─────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    mode: str = "fts"
    conversation_id: Optional[str] = None
    limit: int = 10


class DeleteBulkRequest(BaseModel):
    ids: List[int]


# ── Helpers ────────────────────────────────────────────────────────

def _entries_from_result(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalisiert eine MCP-Tool-Antwort auf eine flache Liste von Eintraegen."""
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    if isinstance(result, dict):
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            entries = structured.get("entries")
            if isinstance(entries, list):
                return [item for item in entries if isinstance(item, dict)]
        for key in ("entries", "results", "items"):
            value = result.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []


def _mcp_error(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(payload, dict):
        return "no_mcp_response"
    if "error" in payload:
        value = payload.get("error")
        return str(value) if value is not None else None
    return None


def _badge_from_policy(meta: Dict[str, Any]) -> str:
    memory_block = meta.get("memory") if isinstance(meta.get("memory"), dict) else {}
    status = meta.get("status") if isinstance(meta.get("status"), dict) else {}
    if bool(status.get("temporary")):
        return "temporary"
    if bool(memory_block.get("do_not_remember")):
        return "do_not_remember"
    mode = str(memory_block.get("mode") or "global_enabled").strip().lower()
    if mode in {"global_enabled", "conversation_only", "disabled"}:
        return mode
    return "global_enabled"


def _policy_response(conversation_id: str, raw_meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    meta = build_conversation_meta(raw_meta, conversation_id) if isinstance(raw_meta, dict) else build_default_conversation_meta(conversation_id)
    policy = build_effective_policy(meta)
    if policy.temporary:
        badge = "temporary"
    elif policy.do_not_remember:
        badge = "do_not_remember"
    else:
        badge = policy.memory_mode.value
    return {
        "conversation_id": conversation_id,
        "memory_mode": policy.memory_mode.value,
        "allow_global_memory_read": policy.allow_global_memory_read,
        "allow_long_term_write": policy.allow_long_term_write,
        "do_not_remember": policy.do_not_remember,
        "temporary": policy.temporary,
        "badge": badge,
    }


# ── Routes ─────────────────────────────────────────────────────────

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
