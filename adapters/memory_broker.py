"""Memory Broker — Multi-Kanal Memory-Abruf mit optionalem Semantic.

Kanäle (Reihenfolge):
  1. FTS5           — immer, scored via rank-Reihenfolge
  2. Layered LIKE   — immer, schichtweise stm → mtm → ltm
  3. Semantic       — optional; Ausfall wird in retrieval_status sichtbar
  4. Recent         — Fill-Kanal nur wenn Treffer-Count < limit

Dedup per content-hash (MD5). Kein id-basierter Cross-Kanal-Dedup, weil
Semantic-IDs aus der Embeddings-Tabelle stammen und nicht mit memory.id
übereinstimmen. Score wird deterministisch pro Kanal vergeben und bei
Dedup-Treffern addiert.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Dict, List

from mcp.client import call_tool
from mcp.tool_result_contracts import MCPToolCallStatus, MCPToolResultEnvelope

_CHANNEL_SCORE: Dict[str, float] = {
    "fts": 3.0,
    "layered": 2.0,
    "semantic": 2.0,
    "recent": 0.5,
}


def _dedup_key(item: Dict[str, Any], channel: str) -> str:
    """Content-Hash als Dedup-Key; Fallback channel:id wenn kein content."""
    content = str(item.get("content") or "").strip()
    if content:
        return hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()
    return f"{channel}:{item.get('id', id(item))}"


_FORBIDDEN_FIELDS = frozenset(
    {"verified", "truth", "evidence", "is_verified", "is_evidence"}
)


def _merge_item(
    item: Dict[str, Any],
    channel: str,
    seen: Dict[str, Dict[str, Any]],
) -> None:
    """Fügt item in seen-Dict ein oder ergänzt score + source_channels.

    Verbotene Top-Level-Felder (truth/evidence/verified) werden aktiv
    entfernt — unabhängig davon, ob heutige Tools sie liefern oder nicht.
    """
    key = _dedup_key(item, channel)
    weight = _CHANNEL_SCORE.get(channel, 0.0)
    if key in seen:
        seen[key]["score"] = seen[key].get("score", 0.0) + weight
        channels = seen[key].setdefault("source_channels", [])
        if channel not in channels:
            channels.append(channel)
    else:
        entry = {k: v for k, v in item.items() if k not in _FORBIDDEN_FIELDS}
        entry["score"] = weight
        entry["source_channels"] = [channel]
        seen[key] = entry


def _list_from(result: MCPToolResultEnvelope) -> List[Dict[str, Any]]:
    """Extrahiert Treffer aus einem erfolgreichen kanonischen Envelope."""
    structured = result.structured_content
    candidates = structured.get("results") if structured is not None else None
    if not isinstance(candidates, (list, tuple)):
        candidates = result.content or ()
    return [dict(item) for item in candidates if isinstance(item, Mapping)]


def retrieve_memory(
    conversation_id: str,
    query: str,
    limit: int = 5,
    timeout_s: float | None = None,
) -> Dict[str, Any]:
    """Konsolidierter Memory-Abruf über FTS, Layered, Semantic, Recent.

    Rückgabe:
      {
        "items": [{"content": ..., "score": float, "source_channels": [...], ...}],
        "retrieval_status": {
          "semantic_unavailable": bool,
          "channels_queried": [...],   # erfolgreich aufgerufen (0–n Treffer)
          "channels_failed":  [...],   # Fehler beim Aufruf
          "channels_with_hits": [...], # haben ≥1 Treffer geliefert
        },
      }
    Bei leerem Query: {"items": [], "skipped": True, "reason": "empty_query"}.
    Keine truth/verified/evidence-Felder.
    """
    query = (query or "").strip()
    if not query:
        return {"items": [], "skipped": True, "reason": "empty_query"}

    if timeout_s is None:
        from config import get_memory_lookup_timeout_s
        timeout_s = get_memory_lookup_timeout_s()

    cid = conversation_id or "global"
    channels_queried: List[str] = []
    channels_failed: List[str] = []
    channels_with_hits: List[str] = []
    seen: Dict[str, Dict[str, Any]] = {}

    def _query(tool: str, args: Dict[str, Any], channel: str) -> None:
        result = call_tool(tool, args, timeout=timeout_s)
        if result.status is not MCPToolCallStatus.SUCCESS:
            channels_failed.append(channel)
            return
        channels_queried.append(channel)
        hits = _list_from(result)
        if hits:
            channels_with_hits.append(channel)
        for hit in hits:
            _merge_item(hit, channel, seen)

    # Kanal 1: FTS5 (immer)
    _query(
        "memory_search_fts",
        {"query": query, "conversation_id": cid, "limit": limit},
        "fts",
    )

    # Kanal 2: Layered LIKE stm → mtm → ltm (immer)
    _query(
        "memory_search_layered",
        {"conversation_id": cid, "query": query, "limit": limit},
        "layered",
    )

    # Kanal 3: Semantic via Embeddings (optional — Ausfall sichtbar, kein Abbruch)
    _query(
        "memory_semantic_search",
        {"query": query, "conversation_id": cid,
         "limit": limit, "min_similarity": 0.5},
        "semantic",
    )

    # Kanal 4: Recent — nur auffüllen wenn Treffer-Count < limit
    def _sorted() -> List[Dict[str, Any]]:
        return sorted(seen.values(), key=lambda x: x.get("score", 0.0), reverse=True)

    items = _sorted()
    if len(items) < limit:
        # limit (nicht remaining) — damit Duplikate aus Recent keine echten
        # Fill-Treffer verdrängen; nach Dedup greift items[:limit] sowieso.
        _query(
            "memory_recent",
            {"conversation_id": cid, "limit": limit},
            "recent",
        )
        items = _sorted()

    return {
        "items": items[:limit],
        "retrieval_status": {
            "semantic_unavailable": "semantic" in channels_failed,
            "channels_queried": channels_queried,
            "channels_failed": channels_failed,
            "channels_with_hits": channels_with_hits,
        },
    }
