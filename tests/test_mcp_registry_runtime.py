import json

import pytest

from mcp.catalog_contracts import (
    CatalogRevocationOutcome,
    MCPDesiredState,
    MCPDiscoveryOutcome,
    MCPDiscoveryStatus,
    MCPToolCatalogSnapshot,
    MCPTransportBindingOutcome,
    MCPTransportBindingStatus,
    make_route,
)
from mcp.hub import MCPHub
from mcp.installer_registry import remove_registry_entry, upsert_registry_entry
from mcp.protocol_contracts import MCPToolsListProtocolResult, MCPToolsListProtocolStatus
from mcp.registry import MCPRegistry


def test_registry_helpers_update_registry_file(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"
    import mcp.config as mcp_config
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    upsert_registry_entry("demo", {"enabled": True, "transport": "http", "url": "http://demo:8000/mcp", "description": "Demo MCP"})

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["demo"]["enabled"] is True
    assert payload["demo"]["transport"] == "http"
    assert payload["demo"]["url"] == "http://demo:8000/mcp"

    remove_registry_entry("demo")
    assert "demo" not in json.loads(registry_path.read_text(encoding="utf-8"))


def test_hub_and_registry_project_only_published_snapshot(monkeypatch):
    transport = object()
    _publish(_snapshot(
        {"memory_fact_load": ("memory-mcp", transport), "memory_fact_save": ("memory-mcp", transport), "demo": ("demo-mcp", object())},
        desired={"memory-mcp": {"tool_intents": {"tools": [{"name": "demo", "keywords": ["k"]}]}}, "demo-mcp": {}},
    ))
    hub = _hub()

    assert hub.list_tools() == [{"name": "memory_fact_load"}, {"name": "memory_fact_save"}, {"name": "demo"}]
    assert hub.get_mcp_for_tool("demo") == "demo-mcp"
    assert MCPRegistry(hub)._tool_registry_version()
    assert MCPRegistry(hub)._tool_intent_keywords("memory-mcp", "demo") == ["k"]


def test_get_mcp_for_tool_miss_does_not_reload(monkeypatch):
    _publish(_snapshot({}))
    hub = _hub()
    reloaded = {"called": 0}
    monkeypatch.setattr(hub, "reload_registry", lambda: reloaded.__setitem__("called", reloaded["called"] + 1))

    assert hub.get_mcp_for_tool("missing") is None
    assert reloaded["called"] == 0


def test_list_tools_success_empty_snapshot_does_not_reload(monkeypatch):
    transport = object()
    _publish(_snapshot({}, desired={"empty": {"enabled": True}}, bound={"empty": transport}, empty={"empty"}))
    hub = _hub()
    reloaded = {"called": 0}
    monkeypatch.setattr(hub, "reload_registry", lambda: reloaded.__setitem__("called", reloaded["called"] + 1))

    assert hub.list_tools() == []
    assert reloaded["called"] == 0


def test_registry_uses_hub_call_tool_without_raw_transport_cache():
    from mcp import tool_result_contracts
    calls = []
    class Hub:
        def __getattr__(self, name):
            if name in {"_transports", "_tools_cache", "_tool_definitions", "_mcp_configs"}:
                raise AssertionError(f"raw cache access forbidden: {name}")
            raise AttributeError(name)

        def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return tool_result_contracts.MCPToolResultEnvelope(tool_result_contracts.MCPToolCallStatus.SUCCESS, structured_content_presence=tool_result_contracts.MCPResultPresence.VALUE, structured_content={"value": "stored"})

    _publish(_snapshot({"memory_fact_load": ("memory-mcp", object()), "memory_fact_save": ("memory-mcp", object())}))
    registry = MCPRegistry(Hub())

    assert registry.get_system_knowledge("key") == "stored"
    registry._save_fact("k", "v")
    assert [name for name, _arguments in calls] == ["memory_fact_load", "memory_fact_save"]


def test_reload_registry_builds_candidate_before_revoke(monkeypatch):
    import mcp.hub as hub_module
    from mcp.catalog_lifecycle import current_catalog_snapshot

    old = _snapshot({"old_tool": ("old", object())}, desired={"old": {}})
    new = _snapshot({"new_tool": ("new", object())}, desired={"new": {}})
    _publish(old)
    events = []

    def build_candidate():
        events.append(("build", tuple(current_catalog_snapshot().desired_mcps)))
        return new

    def revoke(_retire, replacement_snapshot=None):
        assert replacement_snapshot is new
        return events.append(("revoke", tuple(current_catalog_snapshot().desired_mcps))) or CatalogRevocationOutcome(0)

    monkeypatch.setattr(hub_module, "build_catalog_snapshot", build_candidate)
    monkeypatch.setattr(hub_module, "revoke_catalog_routes", revoke)
    monkeypatch.setattr(MCPHub, "_register_tools_in_memory", lambda self: None)

    _hub().reload_registry()

    assert events == [("build", ("old",)), ("revoke", ("old",))]


def test_reload_registry_build_failure_keeps_old_snapshot_and_retirement(monkeypatch):
    import mcp.hub as hub_module
    from mcp.catalog_lifecycle import current_catalog_snapshot

    transport = RetirableTransport()
    old = _snapshot({"old_tool": ("old", transport)}, desired={"old": {}}, bound={"old": transport})
    _publish(old)
    monkeypatch.setattr(hub_module, "build_catalog_snapshot", lambda: (_ for _ in ()).throw(RuntimeError("candidate failed")))
    monkeypatch.setattr(MCPHub, "_register_tools_in_memory", lambda self: None)

    with pytest.raises(RuntimeError):
        _hub().reload_registry()

    assert current_catalog_snapshot() is old
    assert transport.closed == 0


def test_reload_registry_retires_all_old_bound_instances_after_cutover(monkeypatch):
    import mcp.hub as hub_module
    from mcp.catalog_lifecycle import current_catalog_snapshot

    routed, empty, new = RetirableTransport(), RetirableTransport(), RetirableTransport()
    old_snapshot = _snapshot(
        {"old_tool": ("old-routed", routed)},
        desired={"old-routed": {}, "old-empty": {}},
        bound={"old-routed": routed, "old-empty": empty},
        empty={"old-empty"},
    )
    new_snapshot = _snapshot({"new_tool": ("new", new)}, desired={"new": {}}, bound={"new": new})
    _publish(old_snapshot)
    events = []

    def retire(transport):
        events.append(("retire", transport, tuple(current_catalog_snapshot().desired_mcps)))
        transport.shutdown()

    monkeypatch.setattr(hub_module, "build_catalog_snapshot", lambda: new_snapshot)
    monkeypatch.setattr(MCPHub, "_shutdown_transport", staticmethod(retire))
    monkeypatch.setattr(MCPHub, "_register_tools_in_memory", lambda self: None)

    _hub().reload_registry()

    assert current_catalog_snapshot() is new_snapshot
    assert (routed.closed, empty.closed, new.closed) == (1, 1, 0)
    assert [event[2] for event in events] == [("new",), ("new",)]


class RetirableTransport:
    def __init__(self):
        self.closed = 0

    def shutdown(self):
        self.closed += 1


def _hub():
    hub = MCPHub()
    hub._initialized = True
    return hub


def _publish(snapshot):
    from mcp.catalog_lifecycle import publish_catalog, revoke_catalog_routes

    revoke_catalog_routes(lambda _transport: None)
    publish_catalog(snapshot)


def _snapshot(routes, desired=None, bound=None, empty=frozenset()):
    desired = desired or {owner for owner, _transport in routes.values()}
    desired_state = MCPDesiredState({name: dict(config) for name, config in desired.items()} if isinstance(desired, dict) else {name: {} for name in desired}, {})
    bindings = {}
    discovery = {}
    availability = {}
    for mcp_name in desired_state.all_mcps:
        transport = (bound or {}).get(mcp_name)
        bindings[mcp_name] = MCPTransportBindingOutcome(MCPTransportBindingStatus.BOUND, transport=transport) if transport is not None else None
        tools = tuple({"name": tool_name} for tool_name, (owner, _transport) in routes.items() if owner == mcp_name)
        status = MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS if tools and mcp_name not in empty else MCPToolsListProtocolStatus.SUCCESS_EMPTY
        discovery[mcp_name] = MCPDiscoveryOutcome(MCPDiscoveryStatus.PROTOCOL_RESULT, MCPToolsListProtocolResult(status, tools))
        availability[mcp_name] = {"online": True, "routable": False}
    route_map = {tool_name: make_route(tool_name, mcp_name, transport, {"name": tool_name}) for tool_name, (mcp_name, transport) in routes.items()}
    return MCPToolCatalogSnapshot.from_parts(desired_state, bindings, discovery, availability, route_map, {})
