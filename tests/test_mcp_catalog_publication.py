import threading


def test_candidate_is_invisible_before_atomic_publication():
    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot
    from mcp.catalog_lifecycle import current_catalog_snapshot, publish_catalog, revoke_catalog_routes

    revoke_catalog_routes(lambda _transport: None)
    assert current_catalog_snapshot() is None
    snapshot = MCPToolCatalogSnapshot.from_parts(
        desired_state=MCPDesiredState(core_mcps={"a": {}}, custom_mcps={}),
        bindings_by_mcp={"a": None},
        discovery_by_mcp={"a": None},
        availability_by_mcp={"a": {"online": False, "routable": False}},
        routes_by_tool={},
        quarantined_tools={},
    )

    publish_catalog(snapshot)

    assert current_catalog_snapshot() is snapshot


def test_publication_readers_see_whole_snapshots_only():
    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot
    from mcp.catalog_lifecycle import current_catalog_snapshot, publish_catalog

    first = MCPToolCatalogSnapshot.from_parts(MCPDesiredState({"a": {}}, {}), {"a": None}, {"a": None}, {"a": {}}, {}, {})
    second = MCPToolCatalogSnapshot.from_parts(MCPDesiredState({"b": {}}, {}), {"b": None}, {"b": None}, {"b": {}}, {}, {})
    barrier = threading.Barrier(2)
    seen = []

    def reader():
        barrier.wait()
        seen.append(tuple(current_catalog_snapshot().desired_mcps))

    publish_catalog(first)
    thread = threading.Thread(target=reader)
    thread.start()
    barrier.wait()
    publish_catalog(second)
    thread.join()

    assert seen in [[("a",)], [("b",)]]
