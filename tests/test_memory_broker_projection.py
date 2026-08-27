"""Projektions-Regressionsfälle für adapters/memory_broker.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

import adapters.memory_broker as broker_module
from adapters.memory_broker import retrieve_memory
from tests.memory_broker_test_support import _item, _make_call_tool, _ok


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
