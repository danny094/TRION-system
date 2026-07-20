from adapters import orchestrator_sources


def test_build_context_sources_returns_default_keys():
    sources = orchestrator_sources.build_context_sources()
    assert set(sources.keys()) == {"memory", "conversation_meta", "runtime", "active_containers"}
    for name, source in sources.items():
        assert callable(source), f"{name} must be callable"


# ── Memory-Source — aktualisiert für P8-Broker-Delegation ────────────────────
# Die drei folgenden Tests ersetzten die alten Versionen, die
# semantic_search direkt patchten. Nach P8 delegiert _memory_source()
# an retrieve_memory() aus adapters.memory_broker.


def test_memory_source_delegates_to_retrieve_memory(monkeypatch):
    """U1: _memory_source ruft retrieve_memory auf, nicht semantic_search."""
    captured = {}

    def fake_retrieve_memory(conversation_id, query, **kwargs):
        captured["conversation_id"] = conversation_id
        captured["query"] = query
        return {"items": [{"content": "remembered note A"}], "retrieval_status": {}}

    monkeypatch.setattr(orchestrator_sources, "retrieve_memory", fake_retrieve_memory)

    result = orchestrator_sources._memory_source("Erinnerst du dich an TRION?", "conv-1")

    assert captured == {"conversation_id": "conv-1", "query": "Erinnerst du dich an TRION?"}
    assert result["items"] == [{"content": "remembered note A"}]


def test_memory_source_passes_global_conversation_id_to_broker(monkeypatch):
    """U2: Leere conversation_id → Broker erhält 'global'."""
    captured = {}

    def fake_retrieve_memory(conversation_id, query, **kwargs):
        captured["conversation_id"] = conversation_id
        return {"items": [], "retrieval_status": {}}

    monkeypatch.setattr(orchestrator_sources, "retrieve_memory", fake_retrieve_memory)
    orchestrator_sources._memory_source("status", "")
    assert captured["conversation_id"] == "global"


def test_memory_source_skips_when_query_is_empty(monkeypatch):
    """U3: Leere/Whitespace-Query → Broker gibt skip zurück, kein call_tool."""
    def fail_retrieve_memory(conversation_id, query, **kwargs):
        # retrieve_memory selbst gibt bei leerem query {"skipped": True} zurück,
        # ohne call_tool aufzurufen. Dieser Mock stellt sicher, dass der
        # _memory_source-Aufruf überhaupt ankamm und die Logik greift.
        return {"items": [], "skipped": True, "reason": "empty_query"}

    monkeypatch.setattr(orchestrator_sources, "retrieve_memory", fail_retrieve_memory)
    result = orchestrator_sources._memory_source("   ", "conv-1")
    assert result.get("skipped") is True
    assert result.get("reason") == "empty_query"


# ── Neue Tests T10–T12 ────────────────────────────────────────────────────────


def test_memory_source_passes_retrieval_status_through(monkeypatch):
    """T10: retrieval_status aus dem Broker wird von _memory_source weitergegeben."""
    def fake_retrieve_memory(conversation_id, query, **kwargs):
        return {
            "items": [],
            "retrieval_status": {
                "semantic_unavailable": True,
                "channels_queried": ["fts"],
                "channels_failed": ["semantic"],
                "channels_with_hits": [],
            },
        }

    monkeypatch.setattr(orchestrator_sources, "retrieve_memory", fake_retrieve_memory)
    result = orchestrator_sources._memory_source("test", "conv-1")
    assert result["retrieval_status"]["semantic_unavailable"] is True
    assert "fts" in result["retrieval_status"]["channels_queried"]


def test_memory_source_passes_conversation_id_to_broker(monkeypatch):
    """T11: conversation_id wird unverändert an retrieve_memory weitergegeben."""
    captured = {}

    def fake_retrieve_memory(conversation_id, query, **kwargs):
        captured["conversation_id"] = conversation_id
        return {"items": [], "retrieval_status": {}}

    monkeypatch.setattr(orchestrator_sources, "retrieve_memory", fake_retrieve_memory)
    orchestrator_sources._memory_source("text", "conv-99")
    assert captured["conversation_id"] == "conv-99"


def test_memory_source_passes_query_to_broker(monkeypatch):
    """T12: user_text wird als query an retrieve_memory weitergegeben."""
    captured = {}

    def fake_retrieve_memory(conversation_id, query, **kwargs):
        captured["query"] = query
        return {"items": [], "retrieval_status": {}}

    monkeypatch.setattr(orchestrator_sources, "retrieve_memory", fake_retrieve_memory)
    orchestrator_sources._memory_source("Erinnerst du dich?", "conv-1")
    assert captured["query"] == "Erinnerst du dich?"


# ── Unveränderte Tests ─────────────────────────────────────────────────────────


def test_conversation_meta_source_delegates_to_mcp_client(monkeypatch):
    captured = {}

    def fake_get_conversation_meta(conversation_id):
        captured["conversation_id"] = conversation_id
        return {"memory_mode": "session", "do_not_remember": False}

    monkeypatch.setattr(orchestrator_sources, "get_conversation_meta", fake_get_conversation_meta)
    result = orchestrator_sources._conversation_meta_source("hi", "conv-1")
    assert captured == {"conversation_id": "conv-1"}
    assert result == {"memory_mode": "session", "do_not_remember": False}


def test_runtime_source_returns_host_fingerprint():
    result = orchestrator_sources._runtime_source("hi", "conv-1")
    assert set(result.keys()) == {"hostname", "platform", "python", "now_utc"}
    assert isinstance(result["now_utc"], str) and result["now_utc"].endswith("+00:00")
