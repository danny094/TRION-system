import importlib
import json
import sys
from pathlib import Path

from adapters.tool_runner_bridge import get_available_tools
from core.orchestrator.tool_descriptor_projection import descriptor_from_raw
from mcp.catalog_contracts import (
    MCPDesiredState,
    MCPTransportBindingOutcome,
    MCPTransportBindingStatus,
)
from mcp.catalog_lifecycle import publish_catalog, revoke_catalog_routes
from mcp.installer_registry import upsert_registry_entry
from mcp.installer_manifest_normalize import normalize_mcp_manifest
from mcp.installer_tool_intents import build_tool_intent_mirror
from mcp.protocol_contracts import MCPToolsListProtocolResult, MCPToolsListProtocolStatus


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "mcp-servers" / "filesystem"
SERVERS_ROOT = BUNDLE_ROOT.parent


def _server():
    assert BUNDLE_ROOT.is_dir(), "R6 Filesystem MCP product slice is absent"
    if str(SERVERS_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVERS_ROOT))
    return importlib.import_module("filesystem.server")


def test_filesystem_bundle_survives_catalog_bridge_to_descriptor(monkeypatch, tmp_path):
    import mcp.catalog_builder as catalog_builder
    import mcp.config as mcp_config
    import mcp.hub as hub_module

    server = _server()
    manifest = normalize_mcp_manifest(json.loads((BUNDLE_ROOT / "mcp.json").read_text(encoding="utf-8")))
    mirror = build_tool_intent_mirror(BUNDLE_ROOT / "tool_intents.json", bundle_version=manifest["version"])
    registry_path = tmp_path / "mcp_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    upsert_registry_entry("filesystem", {**manifest, "tool_intents": mirror})
    filesystem_config = mcp_config.get_all_mcps()["filesystem"]

    class Transport:
        def list_tools_protocol_result(self):
            return MCPToolsListProtocolResult(
                MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS,
                server.TOOLS,
            )

    transport = Transport()
    desired = MCPDesiredState({}, {"filesystem": filesystem_config})
    monkeypatch.setattr(catalog_builder, "get_mcp_desired_state", lambda: desired)
    monkeypatch.setattr(
        catalog_builder,
        "bind_transport_instance",
        lambda _name, _config: MCPTransportBindingOutcome(
            MCPTransportBindingStatus.BOUND,
            transport=transport,
        ),
    )
    publish_catalog(catalog_builder.build_catalog_snapshot())
    hub = hub_module.MCPHub()
    hub._initialized = True
    monkeypatch.setattr(hub_module, "_hub", hub)

    try:
        raw_tools = get_available_tools()
        descriptors = [descriptor_from_raw(tool) for tool in raw_tools]
    finally:
        revoke_catalog_routes(lambda _transport: None)

    assert manifest["transport"] == "stdio"
    assert manifest["command"] == ".venv/bin/python server.py"
    assert {tool["name"] for tool in raw_tools} == {
        "filesystem_list",
        "filesystem_search",
        "filesystem_metadata",
        "filesystem_read",
    }
    assert all(descriptor is not None for descriptor in descriptors)
    assert all(descriptor.capability_domain == "files" for descriptor in descriptors)
    assert all(descriptor.capability_target_scopes == ["assistant_home"] for descriptor in descriptors)
    assert all(descriptor.output_schema for descriptor in descriptors)
