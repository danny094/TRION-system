"""Regressionstests für adapters/memory_broker.py — P8.

Prüft:
- FTS und Layered werden immer aufgerufen (auch wenn Semantic ok)
- Semantic-Ausfall lässt FTS/Layered-Treffer trotzdem durch
- Recent wird nur als Fill-Kanal genutzt
- retrieval_status.channels_queried/failed/with_hits korrekt gesetzt
- Dedup per content-hash — source_channels und score addiert
- Leere Query → skip, kein call_tool
- Verbotene Felder (truth/evidence/verified) werden aktiv gestripped
- recent_fill mit vollem limit — Duplikate verdrängen keine Fill-Treffer
"""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import patch

import pytest

import adapters.memory_broker as broker_module
from adapters.memory_broker import retrieve_memory


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _ok(items: list) -> Dict[str, Any]:
    """Simuliert eine erfolgreiche call_tool-Antwort mit Items."""
    return {"result": items}


def _err(msg: str = "mcp_timeout") -> Dict[str, Any]:
    """Simuliert eine fehlgeschlagene call_tool-Antwort."""
    return {"error": msg}


def _item(content: str, item_id: int = 1, extra: Dict | None = None) -> Dict[str, Any]:
    base = {"id": item_id, "content": content, "role": "user", "layer": "stm"}
    if extra:
        base.update(extra)
    return base


def _make_call_tool(responses: Dict[str, Any]):
    """Erzeugt einen call_tool-Mock der je nach Tool-Name antwortet."""
    def fake_call_tool(tool_name: str, arguments: Dict, timeout=5.0):
        return responses.get(tool_name, _ok([]))
    return fake_call_tool


# ── T1: Semantic down → FTS-Treffer trotzdem verfügbar ───────────────────────

def test_fts_results_returned_when_semantic_fails():
    """T1: Semantic Ausfall → FTS-Treffer kommen trotzdem durch."""
    fake = _make_call_tool({
        "memory_search_fts": _ok([_item("FTS-Treffer", item_id=1)]),
        "memory_search_layered": _ok([]),
        "memory_semantic_search": _err("ollama_down"),
        "memory_recent": _ok([]),
    })
    with patch.object(broker_module, "call_tool", fake):
        result = retrieve_memory("conv-1", "test query")

    assert any(i["content"] == "FTS-Treffer" for i in result["items"])
    status = result["retrieval_status"]
    assert status["semantic_unavailable"] is True
    assert "semantic" in status["channels_failed"]
    assert "fts" in status["channels_queried"]


# ── T2: FTS wird auch bei Semantic-Erfolg aufgerufen ─────────────────────────

def test_fts_called_even_when_semantic_succeeds():
    """T2: FTS ist kein Fallback — wird immer aufgerufen."""
    called = []

    def fake_call_tool(tool_name: str, arguments: Dict, timeout=5.0):
        called.append(tool_name)
        return _ok([])

    with patch.object(broker_module, "call_tool", fake_call_tool):
        retrieve_memory("conv-1", "test")

    assert "memory_search_fts" in called
    assert "memory_semantic_search" in called


# ── T3: Layered wird immer aufgerufen ────────────────────────────────────────

def test_layered_always_called():
    """T3: Layered LIKE ist kein Fallback — wird immer aufgerufen."""
    called = []

    def fake_call_tool(tool_name: str, arguments: Dict, timeout=5.0):
        called.append(tool_name)
        return _ok([])

    with patch.object(broker_module, "call_tool", fake_call_tool):
        retrieve_memory("conv-1", "test")

    assert "memory_search_layered" in called


# ── T4: Recent wird NICHT aufgerufen wenn Treffer >= limit ───────────────────

def test_recent_not_called_when_limit_reached():
    """T4: Recent bleibt aus wenn FTS/Layered/Semantic bereits limit Treffer liefern."""
    items_5 = [_item(f"item-{i}", item_id=i) for i in range(5)]
    called = []

    def fake_call_tool(tool_name: str, arguments: Dict, timeout=5.0):
        called.append(tool_name)
        return _ok(items_5)

    with patch.object(broker_module, "call_tool", fake_call_tool):
        retrieve_memory("conv-1", "test", limit=5)

    assert "memory_recent" not in called


# ── T5: Recent wird aufgerufen wenn Treffer < limit ──────────────────────────

def test_recent_called_when_below_limit():
    """T5: Recent-Fill wird aktiviert wenn Treffer unter limit."""
    called = []

    def fake_call_tool(tool_name: str, arguments: Dict, timeout=5.0):
        called.append(tool_name)
        return _ok([])

    with patch.object(broker_module, "call_tool", fake_call_tool):
        retrieve_memory("conv-1", "test", limit=5)

    assert "memory_recent" in called


# ── T6: retrieval_status channels korrekt gesetzt ────────────────────────────

def test_retrieval_status_channels_populated():
    """T6: channels_queried, channels_with_hits, channels_failed korrekt."""
    fake = _make_call_tool({
        "memory_search_fts": _ok([_item("fts", item_id=10)]),
        "memory_search_layered": _ok([]),
        "memory_semantic_search": _err("ollama_down"),
    })
    with patch.object(broker_module, "call_tool", fake):
        result = retrieve_memory("conv-1", "test")

    status = result["retrieval_status"]
    assert "fts" in status["channels_queried"]
    assert "layered" in status["channels_queried"]
    assert "fts" in status["channels_with_hits"]
    assert "layered" not in status["channels_with_hits"]
    assert "semantic" in status["channels_failed"]
    assert "semantic" not in status["channels_queried"]


# ── T7: Dedup per content-hash, source_channels und score addiert ────────────

def test_dedup_merges_source_channels_by_content_hash():
    """T7: Gleicher content aus FTS und Layered → einmal im Ergebnis, score addiert."""
    shared = _item("Gleicher Inhalt", item_id=1)
    fake = _make_call_tool({
        "memory_search_fts": _ok([shared]),
        "memory_search_layered": _ok([dict(shared, id=99)]),  # andere id, gleicher content
        "memory_semantic_search": _ok([]),
    })
    with patch.object(broker_module, "call_tool", fake):
        result = retrieve_memory("conv-1", "test")

    items = result["items"]
    matching = [i for i in items if i["content"] == "Gleicher Inhalt"]
    assert len(matching) == 1, "Gleicher content darf nur einmal vorkommen"
    assert set(matching[0]["source_channels"]) == {"fts", "layered"}
    assert matching[0]["score"] == pytest.approx(5.0)  # fts(3) + layered(2)


# ── T8: Leere Query → skip, kein call_tool ───────────────────────────────────

def test_empty_query_skips_all_channels():
    """T8: Leere/Whitespace-Query → sofortiger Skip, kein call_tool."""
    called = []

    def fail_call_tool(tool_name, arguments, timeout=5.0):
        called.append(tool_name)
        raise AssertionError("call_tool must not be called for empty query")

    with patch.object(broker_module, "call_tool", fail_call_tool):
        result = retrieve_memory("conv-1", "   ")

    assert result == {"items": [], "skipped": True, "reason": "empty_query"}
    assert called == []


# ── T9: Keine verbotenen Felder im normalen Ergebnis ─────────────────────────

def test_broker_does_not_emit_forbidden_fields_in_normal_run():
    """T9: items enthalten keine truth/evidence/verified-Felder (normaler Lauf)."""
    fake = _make_call_tool({
        "memory_search_fts": _ok([_item("normal content")]),
        "memory_search_layered": _ok([]),
        "memory_semantic_search": _ok([]),
    })
    with patch.object(broker_module, "call_tool", fake):
        result = retrieve_memory("conv-1", "test")

    for item in result["items"]:
        assert "verified" not in item
        assert "truth" not in item
        assert "evidence" not in item
        assert "is_verified" not in item
        assert "is_evidence" not in item


# ── T10: Verbotene Felder werden aktiv gestripped ────────────────────────────

def test_broker_strips_truth_evidence_fields():
    """T10: Tool liefert truth/verified → Broker strippt sie aktiv."""
    dirty_item = _item("secure content", item_id=5, extra={
        "truth": "absolute",
        "verified": True,
        "evidence": ["some-doc"],
        "is_verified": True,
    })
    fake = _make_call_tool({
        "memory_search_fts": _ok([dirty_item]),
        "memory_search_layered": _ok([]),
        "memory_semantic_search": _ok([]),
    })
    with patch.object(broker_module, "call_tool", fake):
        result = retrieve_memory("conv-1", "test")

    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["content"] == "secure content"
    assert "truth" not in item
    assert "verified" not in item
    assert "evidence" not in item
    assert "is_verified" not in item


# ── T11: Recent-Fill mit vollem limit — Duplikate verdrängen keine Treffer ───

def test_recent_fill_survives_duplicates():
    """T11: Recent wird mit limit (nicht remaining) aufgerufen.

    Szenario: 2 unique Items aus FTS, limit=4. Recent gibt 4 Items zurück,
    davon 2 Duplikate von FTS (gleicher content). Broker muss trotzdem auf
    mindestens 2 neue Items aus Recent kommen, weil er mit limit=4 abruft.
    """
    fts_items = [_item(f"fts-{i}", item_id=i) for i in range(2)]
    recent_items = [
        _item("fts-0", item_id=100),    # Duplikat von fts_items[0]
        _item("fts-1", item_id=101),    # Duplikat von fts_items[1]
        _item("recent-only-A", item_id=102),
        _item("recent-only-B", item_id=103),
    ]
    fake = _make_call_tool({
        "memory_search_fts": _ok(fts_items),
        "memory_search_layered": _ok([]),
        "memory_semantic_search": _ok([]),
        "memory_recent": _ok(recent_items),
    })
    with patch.object(broker_module, "call_tool", fake):
        result = retrieve_memory("conv-1", "test", limit=4)

    contents = {i["content"] for i in result["items"]}
    assert "recent-only-A" in contents, "Recent-Fill-Treffer fehlen trotz Duplikaten"
    assert "recent-only-B" in contents
