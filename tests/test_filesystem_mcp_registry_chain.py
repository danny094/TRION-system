import importlib
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
from mcp.installer_manifest import load_bundle_manifest
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
    manifest = load_bundle_manifest(BUNDLE_ROOT)
    registry_path = tmp_path / "mcp_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", registry_path)
    upsert_registry_entry("filesystem", manifest)
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
    expected_operations = {
        "filesystem_list": "list",
        "filesystem_search": "search",
        "filesystem_metadata": "inspect",
        "filesystem_read": "read",
    }
    live_by_name = {tool["name"]: tool for tool in server.TOOLS}
    intents_by_name = {
        tool["name"]: tool for tool in manifest["tool_intents"]["tools"]
    }
    for descriptor in descriptors:
        assert descriptor is not None
        intent = intents_by_name[descriptor.name]
        live = live_by_name[descriptor.name]
        assert descriptor.description == live["description"]
        assert descriptor.source == "filesystem"
        assert descriptor.schema == live["inputSchema"]
        assert descriptor.intent_description == intent["description"]
        assert descriptor.intent_examples == intent["examples"]
        assert descriptor.intent_keywords == intent["keywords"]
        assert descriptor.capability_domain == "files"
        assert descriptor.capability_operation == expected_operations[descriptor.name]
        assert descriptor.capability_entity_types == intent["supports_entities"]
        assert descriptor.capability_evidence_types == ["file_context"]
        assert descriptor.capability_required_args == intent["requires"]
        assert descriptor.capability_risk == "read_only"
        assert descriptor.capability_target_scopes == ["assistant_home"]
        assert descriptor.capability_freshness_support == "live_only"
        assert descriptor.capability_output_schema == "mcp_output_schema"
        assert descriptor.output_schema == live["outputSchema"]
        assert descriptor.tool_role == "primary"
        assert descriptor.can_answer_directly is True
        assert descriptor.mirror_schema_version == 2
        assert descriptor.mirror_source_sha256 == manifest["tool_intents"]["source_sha256"]
        assert descriptor.mirror_bundle_version == manifest["version"]
