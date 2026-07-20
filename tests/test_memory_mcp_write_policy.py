import sqlite3
import sys
import types
import importlib

from memory.memory_mcp import config as memory_config
from memory.memory_mcp import database as memory_database
from memory.memory_mcp.db import conversation_meta as conversation_meta_db
from memory.memory_mcp.db import facts as facts_db
from memory.memory_mcp.db import memory as memory_db
from memory.memory_mcp.db import schema as schema_db
from utils.memory_defaults import (
    MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
    MEMORY_DEFAULT_MODE_KEY,
)
from utils.settings import settings


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, fn):
        self.tools[fn.__name__] = fn
        return fn


class _DummyVectorStore:
    def add(self, **kwargs):
        return None


def _import_memory_tools():
    graph_module = types.SimpleNamespace(
        get_graph_store=lambda: None,
        build_node_with_edges=lambda **kwargs: None,
    )
    vector_store_module = types.SimpleNamespace(get_vector_store=lambda: _DummyVectorStore())
    sys.modules.setdefault("graph", graph_module)
    sys.modules.setdefault("vector_store", vector_store_module)
    return importlib.import_module("memory.memory_mcp.tools")


def _set_db_path(monkeypatch, tmp_path):
    db_path = str(tmp_path / "memory-policy.db")
    monkeypatch.setattr(memory_config, "DB_PATH", db_path)
    monkeypatch.setattr(schema_db, "DB_PATH", db_path)
    monkeypatch.setattr(memory_db, "DB_PATH", db_path)
    monkeypatch.setattr(facts_db, "DB_PATH", db_path)
    monkeypatch.setattr(conversation_meta_db, "DB_PATH", db_path)
    memory_database.init_db()
    return db_path


def _register_tools(monkeypatch):
    memory_tools = _import_memory_tools()
    fake = _FakeMCP()
    memory_tools.register_tools(fake)
    return fake.tools


def _clear_memory_default_settings():
    for key in (MEMORY_DEFAULT_MODE_KEY, MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY):
        settings.settings.pop(key, None)


def test_memory_save_blocks_ltm_when_default_mode_is_disabled_without_meta(monkeypatch, tmp_path):
    db_path = _set_db_path(monkeypatch, tmp_path)
    _clear_memory_default_settings()
    settings.settings[MEMORY_DEFAULT_MODE_KEY] = "disabled"
    settings.settings[MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY] = True
    tools = _register_tools(monkeypatch)

    try:
        result = tools["memory_save"]("conv-no-meta", "assistant", "remember this", layer="ltm")
    finally:
        _clear_memory_default_settings()

    assert result["structuredContent"]["saved"] is False
    assert result["structuredContent"]["denied"] is True
    assert result["structuredContent"]["reason"] == "do_not_remember"

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memory WHERE conversation_id = ?", ("conv-no-meta",)).fetchone()[0]
    assert count == 0


def test_memory_save_blocks_ltm_when_conversation_is_temporary(monkeypatch, tmp_path):
    db_path = _set_db_path(monkeypatch, tmp_path)
    conversation_meta_db.upsert_conversation_meta(
        "conv-temp",
        {"status": {"temporary": True}},
    )
    tools = _register_tools(monkeypatch)

    result = tools["memory_save"]("conv-temp", "assistant", "remember this", layer="ltm")

    assert result["structuredContent"]["saved"] is False
    assert result["structuredContent"]["denied"] is True
    assert result["structuredContent"]["reason"] == "temporary_conversation"

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memory WHERE conversation_id = ?", ("conv-temp",)).fetchone()[0]
    assert count == 0


def test_memory_save_allows_stm_when_do_not_remember_is_true(monkeypatch, tmp_path):
    db_path = _set_db_path(monkeypatch, tmp_path)
    conversation_meta_db.upsert_conversation_meta(
        "conv-local",
        {"memory": {"do_not_remember": True}},
    )
    tools = _register_tools(monkeypatch)

    result = tools["memory_save"]("conv-local", "assistant", "session only", layer="stm")

    assert result["structuredContent"]["id"] > 0
    assert result["structuredContent"]["layer"] == "stm"

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM memory WHERE conversation_id = ?", ("conv-local",)).fetchone()[0]
    assert count == 1


def test_memory_fact_save_blocks_ltm_when_memory_is_disabled(monkeypatch, tmp_path):
    db_path = _set_db_path(monkeypatch, tmp_path)
    conversation_meta_db.upsert_conversation_meta(
        "conv-disabled",
        {"memory": {"mode": "disabled"}},
    )
    tools = _register_tools(monkeypatch)

    result = tools["memory_fact_save"]("conv-disabled", "repo", "TRION", layer="ltm")

    assert result["structuredContent"]["saved"] is False
    assert result["structuredContent"]["denied"] is True
    assert result["structuredContent"]["reason"] == "memory_disabled"

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM facts WHERE conversation_id = ?", ("conv-disabled",)).fetchone()[0]
    assert count == 0
