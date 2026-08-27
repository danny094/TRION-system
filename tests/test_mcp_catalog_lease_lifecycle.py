import pytest


class Transport:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, args):
        self.calls.append((name, args))
        return {"ok": True}


def test_acquire_binds_exact_route_and_dispatch_releases_token():
    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot, make_route
    from mcp.catalog_dispatch import dispatch_acquired_route
    from mcp.catalog_lifecycle import acquire_route, publish_catalog

    transport = Transport()
    snapshot = MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState({"m": {}}, {}), {"m": None}, {"m": None}, {"m": {}},
        {"tool": make_route("tool", "m", transport, {"name": "tool"})}, {},
    )
    publish_catalog(snapshot)
    token = acquire_route("tool")

    assert dispatch_acquired_route(token, {"x": 1}) == {"ok": True}
    assert transport.calls == [("tool", {"x": 1})]


def test_revocation_stops_new_acquires():
    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot
    from mcp.catalog_lifecycle import acquire_route, publish_catalog, revoke_catalog_routes

    publish_catalog(MCPToolCatalogSnapshot.from_parts(MCPDesiredState({"m": {}}, {}), {"m": None}, {"m": None}, {"m": {}}, {}, {}))
    revoke_catalog_routes(lambda _transport: None)

    with pytest.raises(RuntimeError):
        acquire_route("missing")
