from mcp.protocol_contracts import MCPToolsListProtocolResult, MCPToolsListProtocolStatus


class Transport:
    def list_tools_protocol_result(self):
        return MCPToolsListProtocolResult(MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS, [{"name": "dupe"}])


def test_duplicate_tool_names_are_quarantined_without_first_wins(monkeypatch):
    import mcp.catalog_builder as builder
    from mcp.catalog_contracts import MCPDesiredState

    desired = MCPDesiredState(
        core_mcps={"a": {"enabled": True, "transport": "http"}, "b": {"enabled": True, "transport": "http"}},
        custom_mcps={},
    )
    monkeypatch.setattr(builder, "get_mcp_desired_state", lambda: desired)
    monkeypatch.setattr(builder, "bind_transport_instance", lambda _n, _c: builder.MCPTransportBindingOutcome(
        builder.MCPTransportBindingStatus.BOUND, transport=Transport(),
    ))

    snapshot = builder.build_catalog_snapshot()

    assert "dupe" not in snapshot.routes_by_tool
    assert snapshot.quarantined_tools["dupe"] == ("a", "b")
