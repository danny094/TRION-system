import asyncio

from tests.memory_routes_test_support import _json, _load_memory_routes


def test_policy_endpoint_derives_badge_from_meta(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(
        memory_routes,
        "get_conversation_meta",
        lambda conv: {
            "memory": {"mode": "conversation_only", "do_not_remember": False},
            "status": {"temporary": False},
        },
    )
    response = asyncio.run(memory_routes.memory_conversation_policy(conversation_id="conv-a"))
    data = _json(response)
    assert data["memory_mode"] == "conversation_only"
    assert data["badge"] == "conversation_only"
    assert data["allow_global_memory_read"] is False
    assert data["allow_long_term_write"] is True


def test_policy_endpoint_returns_temporary_badge(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(
        memory_routes,
        "get_conversation_meta",
        lambda conv: {
            "memory": {"mode": "global_enabled"},
            "status": {"temporary": True},
        },
    )
    response = asyncio.run(memory_routes.memory_conversation_policy(conversation_id="conv-tmp"))
    data = _json(response)
    assert data["badge"] == "temporary"
    assert data["temporary"] is True
    assert data["allow_long_term_write"] is False


def test_policy_endpoint_defaults_when_no_meta(monkeypatch):
    memory_routes = _load_memory_routes()
    monkeypatch.setattr(memory_routes, "get_conversation_meta", lambda conv: None)
    monkeypatch.setattr(
        memory_routes,
        "build_default_conversation_meta",
        lambda conv: memory_routes.build_conversation_meta(
            {"conversation_id": conv, "memory": {"mode": "conversation_only"}},
            conv,
        ),
    )
    response = asyncio.run(memory_routes.memory_conversation_policy(conversation_id="conv-new"))
    data = _json(response)
    assert data["memory_mode"] == "conversation_only"
    assert data["badge"] == "conversation_only"
    assert data["allow_global_memory_read"] is False
