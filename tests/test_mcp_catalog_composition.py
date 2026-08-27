import pytest

from mcp.protocol_contracts import MCPToolsListProtocolResult, MCPToolsListProtocolStatus


class Transport:
    def __init__(self, tools):
        self.tools = tools

    def list_tools_protocol_result(self):
        return MCPToolsListProtocolResult(MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS, self.tools)


def test_catalog_candidate_is_total_immutable_and_routes_only_success_with_tools(monkeypatch):
    import mcp.catalog_builder as builder
    from mcp.catalog_contracts import MCPDesiredState

    desired = MCPDesiredState(
        core_mcps={
            "routable": {"enabled": True, "transport": "http"},
            "empty": {"enabled": True, "transport": "http"},
            "disabled": {"enabled": False, "transport": "http"},
        },
        custom_mcps={},
    )
    monkeypatch.setattr(builder, "get_mcp_desired_state", lambda: desired)
    original_bind = builder.bind_transport_instance

    def bind(name, config):
        if name == "disabled":
            return original_bind(name, config)
        transport = Transport([{"name": "tool"}]) if name == "routable" else EmptyTransport()
        return builder.MCPTransportBindingOutcome(builder.MCPTransportBindingStatus.BOUND, transport=transport)

    monkeypatch.setattr(builder, "bind_transport_instance", bind)
    snapshot = builder.build_catalog_snapshot()

    assert set(snapshot.desired_mcps) == {"routable", "empty", "disabled"}
    assert set(snapshot.bindings_by_mcp) == set(snapshot.availability_by_mcp)
    assert snapshot.routes_by_tool["tool"]["mcp_name"] == "routable"
    assert "empty" in snapshot.desired_mcps
    with pytest.raises(TypeError):
        snapshot.routes_by_tool["new"] = object()


class EmptyTransport:
    def list_tools_protocol_result(self):
        return MCPToolsListProtocolResult(MCPToolsListProtocolStatus.SUCCESS_EMPTY)
