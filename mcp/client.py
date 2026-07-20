"""
MCP Client - High-level Hilfsfunktionen für Tool-Calls und Memory-Zugriff.

Verantwortlich für:
- Einheitlicher call_tool() Wrapper (routet über Hub)
- Memory-Helpers: autosave, fact retrieval, semantic search, graph search
"""

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Dict, List, Optional
import os

from utils.logger import log_debug, log_error, log_info, log_warning

_MAX_WORKERS = max(4, min(64, int(os.getenv("MCP_CLIENT_MAX_WORKERS", "16"))))
_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="mcp-client")


# ── Core ───────────────────────────────────────────────────────────

def call_tool(name: str, arguments: Dict[str, Any], timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Ruft ein Tool über den Hub auf."""
    try:
        from mcp.hub import get_hub
        future = _EXECUTOR.submit(get_hub().call_tool, name, arguments)
        result = future.result(timeout=max(0.2, float(timeout)))
        if result and not isinstance(result, dict):
            return {"result": result}
        if result and "error" not in result:
            return {"result": result}
        return result
    except FuturesTimeout:
        log_error(f"[MCPClient] Timeout: tool={name} timeout={timeout}s")
        return {"error": f"mcp_timeout:{name}:{timeout}s"}
    except Exception as e:
        log_error(f"[MCPClient] call_tool failed: {e}")
        return {"error": str(e)}


# ── Memory Helpers ─────────────────────────────────────────────────

def autosave_assistant(
    conversation_id: str,
    content: str,
    layer: str = "auto",
    classifier_result: Optional[dict] = None,
) -> None:
    """Speichert eine Assistant-Antwort ins Memory."""
    if not content:
        return
    call_tool("memory_save", {
        "conversation_id": conversation_id or "global",
        "role": "assistant",
        "content": content,
        "tags": "",
        "layer": layer,
    })
    if not classifier_result:
        return
    if (classifier_result.get("save")
            and classifier_result.get("type") == "fact"
            and classifier_result.get("key")
            and classifier_result.get("value")):
        call_tool("memory_fact_save", {
            "conversation_id": conversation_id or "global",
            "subject": classifier_result.get("subject", "user"),
            "key": classifier_result["key"],
            "value": classifier_result["value"],
            "layer": "ltm",
        })


def get_fact(conversation_id: str, key: str, timeout_s: Optional[float] = None) -> Optional[str]:
    """Lädt einen strukturierten Fakt aus dem Memory."""
    if timeout_s is None:
        from config import get_memory_lookup_timeout_s
        timeout_s = get_memory_lookup_timeout_s()
    resp = call_tool("memory_fact_load", {
        "conversation_id": conversation_id or "global",
        "key": key,
    }, timeout=timeout_s)
    if not resp:
        return None
    result = resp.get("result") or resp
    if isinstance(result, dict):
        val = (result.get("value")
               or result.get("structuredContent", {}).get("value")
               or result.get("structuredContent", {}).get("result"))
        if val:
            return val
        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    parsed = json.loads(item["text"])
                    v = parsed.get("result") or parsed.get("structuredContent", {}).get("value")
                    if v:
                        return v
                except Exception:
                    pass
    return None


def search_memory(conversation_id: str, query: str, timeout_s: Optional[float] = None) -> str:
    """Textsuche im Memory als Fallback."""
    if timeout_s is None:
        from config import get_memory_lookup_timeout_s
        timeout_s = get_memory_lookup_timeout_s()
    resp = call_tool("memory_search_layered", {
        "conversation_id": conversation_id or "global",
        "query": query,
    }, timeout=timeout_s)
    if not resp:
        return ""
    entries = resp.get("result", [])
    if entries and isinstance(entries, list):
        return entries[0].get("content", "")
    return ""


def semantic_search(
    conversation_id: str,
    query: str,
    limit: int = 5,
    timeout_s: Optional[float] = None,
) -> List[Dict]:
    """Semantische Suche im Memory via Embeddings."""
    if timeout_s is None:
        from config import get_memory_lookup_timeout_s
        timeout_s = get_memory_lookup_timeout_s()
    resp = call_tool("memory_semantic_search", {
        "query": query,
        "conversation_id": conversation_id or "global",
        "limit": limit,
        "min_similarity": 0.5,
    }, timeout=timeout_s)
    if not resp:
        return []
    result = resp.get("result", {})
    if isinstance(result, dict):
        return (result.get("structuredContent", {}).get("results")
                or result.get("results", []))
    return []


def graph_search(
    conversation_id: str,
    query: str,
    depth: int = 2,
    limit: int = 10,
    timeout_s: Optional[float] = None,
) -> List[Dict]:
    """Graph-basierte Suche für verbundene Informationen."""
    if timeout_s is None:
        from config import get_memory_lookup_timeout_s
        timeout_s = get_memory_lookup_timeout_s()
    resp = call_tool("memory_graph_search", {
        "query": query,
        "conversation_id": conversation_id or "global",
        "depth": depth,
        "limit": limit,
    }, timeout=timeout_s)
    if not resp:
        return []
    result = resp.get("result", {})
    if isinstance(result, dict):
        return (result.get("structuredContent", {}).get("results")
                or result.get("results", []))
    return []


def get_conversation_meta(conversation_id: str, timeout_s: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Load persisted conversation metadata when available."""
    if timeout_s is None:
        from config import get_memory_lookup_timeout_s
        timeout_s = get_memory_lookup_timeout_s()
    resp = call_tool(
        "conversation_meta_get",
        {"conversation_id": conversation_id or "global"},
        timeout=timeout_s,
    )
    if not resp or resp.get("error"):
        return None
    result = resp.get("result") or resp
    if isinstance(result, dict):
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            meta = structured.get("meta")
            return meta if isinstance(meta, dict) else None
        meta = result.get("meta")
        return meta if isinstance(meta, dict) else None
    return None
