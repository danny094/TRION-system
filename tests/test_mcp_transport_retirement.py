import threading

import pytest

from mcp.catalog_contracts import MCPTransportBindingOutcome, MCPTransportBindingStatus


class Transport:
    def __init__(self, release):
        self.release = release
        self.closed = 0

    def call_tool(self, _name, _args):
        self.release.wait()
        return {"done": True}

    def shutdown(self):
        self.closed += 1


class RetirementFailure(Exception):
    pass


def test_revocation_drains_active_call_before_single_retirement():
    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot, make_route
    from mcp.catalog_dispatch import dispatch_acquired_route
    from mcp.catalog_lifecycle import acquire_route, publish_catalog, revoke_catalog_routes

    release = threading.Event()
    transport = Transport(release)
    snapshot = MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState({"m": {}}, {}), {"m": None}, {"m": None}, {"m": {}},
        {"tool": make_route("tool", "m", transport, {"name": "tool"})}, {},
    )
    publish_catalog(snapshot)
    token = acquire_route("tool")
    finished = threading.Event()
    thread = threading.Thread(target=lambda: (dispatch_acquired_route(token, {}), finished.set()))
    thread.start()
    retire_started = threading.Event()

    def retire():
        retire_started.set()
        revoke_catalog_routes(lambda item: item.shutdown())

    retire_thread = threading.Thread(target=retire)
    retire_thread.start()
    retire_started.wait()
    assert transport.closed == 0
    release.set()
    thread.join()
    retire_thread.join()

    assert finished.is_set()
    assert transport.closed == 1
    revoke_catalog_routes(lambda item: item.shutdown())
    assert transport.closed == 1


def test_revocation_attempts_remaining_transports_before_reporting_failure():
    from mcp.catalog_contracts import MCPDesiredState, MCPToolCatalogSnapshot, make_route
    from mcp.catalog_lifecycle import publish_catalog, revoke_catalog_routes

    release = threading.Event()
    first_transport = Transport(release)
    second_transport = Transport(release)
    failure = RetirementFailure()
    calls = []

    snapshot = MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState({"first": {}, "second": {}}, {}),
        {
            "first": MCPTransportBindingOutcome(
                MCPTransportBindingStatus.BOUND, transport=first_transport
            ),
            "second": MCPTransportBindingOutcome(
                MCPTransportBindingStatus.BOUND, transport=second_transport
            ),
        },
        {"first": None, "second": None},
        {"first": {}, "second": {}},
        {
            "first_tool": make_route(
                "first_tool", "first", first_transport, {"name": "first_tool"}
            ),
            "second_tool": make_route(
                "second_tool", "second", second_transport, {"name": "second_tool"}
            ),
        },
        {},
    )
    publish_catalog(snapshot)

    def retire(transport):
        calls.append(transport)
        if transport is first_transport:
            raise failure

    with pytest.raises(ExceptionGroup) as raised:
        revoke_catalog_routes(retire)

    assert calls == [first_transport, second_transport]
    assert raised.value.exceptions == (failure,)
