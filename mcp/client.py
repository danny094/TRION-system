"""
MCP Client - High-level Hilfsfunktionen für Tool-Calls und Memory-Zugriff.

Verantwortlich für:
- Einheitlicher call_tool() Wrapper (routet über Hub)
- Memory-Helpers: autosave, fact retrieval, semantic search, graph search
"""

import json
from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from mcp import client_handoff
from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope
from utils.logger import log_debug, log_info, log_warning


# ── Core ───────────────────────────────────────────────────────────

def call_tool(
    name: str,
    arguments: Dict[str, Any],
    timeout: float = 5.0,
) -> MCPToolResultEnvelope:
    """Ruft ein Tool über den Hub auf."""
    return client_handoff.call_tool_result(name, arguments, timeout)


def _successful_structured(result: MCPToolResultEnvelope) -> Optional[Mapping[str, Any]]:
    if result.status is not MCPToolCallStatus.SUCCESS:
        return None
    return result.structured_content


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
    result = _successful_structured(resp)
    if result is not None:
        val = result.get("value") or result.get("result")
        if val:
            return val
    if resp.status is MCPToolCallStatus.SUCCESS:
        for item in resp.content or ():
            if isinstance(item, Mapping) and item.get("type") == "text":
                try:
                    parsed = json.loads(item["text"])
                except (KeyError, TypeError, json.JSONDecodeError):
                    continue
                if isinstance(parsed, Mapping):
                    value = parsed.get("result") or parsed.get("value")
                    if value:
                        return value
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
    result = _successful_structured(resp)
    entries = result.get("result", []) if result is not None else []
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
    result = _successful_structured(resp)
    if result is not None:
        return result.get("results", [])
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
    result = _successful_structured(resp)
    if result is not None:
        return result.get("results", [])
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
    result = _successful_structured(resp)
    if result is not None:
        meta = result.get("meta")
        return dict(meta) if isinstance(meta, Mapping) else None
    return None
