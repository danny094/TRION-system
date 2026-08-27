def test_hub_listing_registry_and_installer_project_snapshot(monkeypatch):
    import json

    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot, make_route
    from mcp.hub import MCPHub
    from mcp.installer_manage_routes import _tools_for_mcp
    from mcp.registry import MCPRegistry

    transport = object()
    route = make_route(
        "tool",
        "m",
        transport,
        {
            "name": "tool",
            "description": "d",
            "inputSchema": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
        },
    )
    snapshot = MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState(
            {
                "m": {
                    "enabled": True,
                    "tool_intents": {"tools": [{"name": "tool", "keywords": ["k"]}]},
                    "ui": {
                        "launchpad": {"enabled": True, "label": "M"},
                        "settings": {"enabled": True, "mode": "config"},
                    },
                }
            },
            {},
        ),
        {"m": None}, {"m": None}, {"m": {"online": True, "routable": True}}, {"tool": route}, {},
    )
    from mcp.catalog_lifecycle import publish_catalog

    publish_catalog(snapshot)

    hub = MCPHub()
    hub._initialized = True
    projected_tools = hub.list_tools()
    assert projected_tools[0]["inputSchema"]["properties"]["value"]["type"] == "string"
    assert projected_tools[0]["outputSchema"]["properties"]["result"]["type"] == "string"
    json.dumps(projected_tools)
    assert projected_tools[0]["inputSchema"]["required"] == ["value"]
    assert hub.get_mcp_for_tool("tool") == "m"
    projected = hub.list_mcps()[0]
    assert projected["online"] is True
    assert projected["ui"] == {
        "launchpad": {"enabled": True, "label": "M"},
        "settings": {"enabled": True, "mode": "config"},
    }
    json.dumps(projected)
    assert _tools_for_mcp(hub, "m")[0]["name"] == "tool"
    assert MCPRegistry(hub)._tool_intent_keywords("m", "tool") == ["k"]


def test_registry_uses_hub_call_tool_not_raw_transport():
    from mcp.registry import MCPRegistry
    from mcp.tool_result_contracts import (
        MCPResultPresence,
        MCPToolCallStatus,
        MCPToolResultEnvelope,
    )

    class Hub:
        def __init__(self):
            self.calls = []

        def call_tool(self, name, arguments):
            self.calls.append((name, arguments))
            return MCPToolResultEnvelope(
                MCPToolCallStatus.SUCCESS,
                structured_content_presence=MCPResultPresence.VALUE,
                structured_content={"value": "v"},
            )

    hub = Hub()
    registry = MCPRegistry(hub)

    assert registry.get_system_knowledge("key") == "v"
    registry._save_fact("k", "v")
    assert [call[0] for call in hub.calls] == ["memory_fact_load", "memory_fact_save"]
