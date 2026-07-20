import json

from mcp.registry import MCPRegistry
from mcp.hub import MCPHub
from mcp.installer_registry import remove_registry_entry, upsert_registry_entry


def test_registry_helpers_update_registry_file(monkeypatch, tmp_path):
    registry_path = tmp_path / "mcp_registry.json"

    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)

    upsert_registry_entry(
        "demo",
        {
            "enabled": True,
            "transport": "http",
            "url": "http://demo:8000/mcp",
            "description": "Demo MCP",
        },
    )

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload["demo"]["enabled"] is True
    assert payload["demo"]["transport"] == "http"
    assert payload["demo"]["url"] == "http://demo:8000/mcp"

    remove_registry_entry("demo")

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "demo" not in payload


def test_hub_reload_registry_adds_and_removes_servers(monkeypatch):
    states = [
        {
            "alpha": {
                "enabled": True,
                "transport": "http",
                "url": "http://alpha:8000/mcp",
                "description": "Alpha",
            }
        },
        {
            "beta": {
                "enabled": True,
                "transport": "http",
                "url": "http://beta:8000/mcp",
                "description": "Beta",
            }
        },
    ]
    index = {"value": 0}

    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "get_enabled_mcps", lambda: states[index["value"]])
    monkeypatch.setattr(mcp_config, "get_all_mcps", lambda: states[index["value"]])
    monkeypatch.setattr(MCPHub, "_register_tools_in_memory", lambda self: None)

    def fake_init_transport(self, mcp_name, config):
        self._transports[mcp_name] = object()
        self._mcp_configs[mcp_name] = dict(config)

    def fake_discover_tools(hub, mcp_name):
        hub._tools_cache[f"{mcp_name}_tool"] = mcp_name
        hub._tool_definitions[f"{mcp_name}_tool"] = {"name": f"{mcp_name}_tool"}

    monkeypatch.setattr(MCPHub, "_init_transport", fake_init_transport)
    import mcp.hub as hub_module

    monkeypatch.setattr(hub_module, "discover_tools", fake_discover_tools)

    hub = MCPHub()
    hub.reload_registry()

    assert set(hub._transports.keys()) == {"alpha"}
    assert hub.get_mcp_for_tool("alpha_tool") == "alpha"

    index["value"] = 1
    hub.reload_registry()

    assert set(hub._transports.keys()) == {"beta"}
    assert hub.get_mcp_for_tool("alpha_tool") is None
    assert hub.get_mcp_for_tool("beta_tool") == "beta"


def test_registry_prefers_transport_that_owns_memory_fact_load_tool():
    transport = object()
    registry = MCPRegistry(
        type(
            "Hub",
            (),
            {
                "_tool_definitions": {},
                "_tools_cache": {"memory_fact_load": "memory-mcp"},
                "_transports": {"memory-mcp": transport, "sql-memory": object()},
            },
        )()
    )

    assert registry._memory_transport() is transport


def test_hub_list_tools_reloads_when_healthy_mcp_has_zero_tools(monkeypatch):
    hub = MCPHub()
    hub._initialized = True
    hub._transports = {"memory-mcp": type("Transport", (), {"health_check": lambda self: True})()}
    hub._mcp_configs = {"memory-mcp": {"enabled": True}}

    reloaded = {"called": 0}

    def fake_reload():
        reloaded["called"] += 1
        hub._tools_cache["memory_search"] = "memory-mcp"
        hub._tool_definitions["memory_search"] = {"name": "memory_search"}

    monkeypatch.setattr(hub, "reload_registry", fake_reload)

    tools = hub.list_tools()

    assert reloaded["called"] == 1
    assert tools == [{"name": "memory_search"}]


def test_hub_reloads_on_tool_miss(monkeypatch):
    hub = MCPHub()
    hub._initialized = True
    hub._transports = {"memory-mcp": object()}
    hub._mcp_configs = {"memory-mcp": {"enabled": True}}

    def fake_reload():
        hub._tools_cache["memory_search"] = "memory-mcp"

    monkeypatch.setattr(hub, "reload_registry", fake_reload)

    assert hub.get_mcp_for_tool("memory_search") == "memory-mcp"
