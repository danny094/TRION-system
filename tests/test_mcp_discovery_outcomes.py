import pytest

from mcp.protocol_contracts import MCPToolsListProtocolResult, MCPToolsListProtocolStatus


class Transport:
    def __init__(self, result=None, exc=None):
        self.calls = 0
        self.result = result
        self.exc = exc

    def list_tools_protocol_result(self):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.result


def test_binding_status_contracts_are_fail_closed():
    from mcp.catalog_contracts import MCPTransportBindingOutcome, MCPTransportBindingStatus

    assert {item.name for item in MCPTransportBindingStatus} == {
        "BOUND", "DISABLED", "CONSTRUCTION_FAILED", "MISSING",
    }
    with pytest.raises(ValueError):
        MCPTransportBindingOutcome(MCPTransportBindingStatus.BOUND)
    with pytest.raises(ValueError):
        MCPTransportBindingOutcome(MCPTransportBindingStatus.DISABLED, diagnostic="x")
    with pytest.raises(ValueError):
        MCPTransportBindingOutcome(MCPTransportBindingStatus.CONSTRUCTION_FAILED)


def test_discovery_is_total_and_only_bound_calls_typed_protocol():
    from mcp.catalog_contracts import MCPDesiredState, MCPTransportBindingOutcome, MCPTransportBindingStatus
    from mcp.catalog_discovery import discover_catalog_outcomes

    desired = MCPDesiredState(
        core_mcps={"ok": {}, "disabled": {}, "missing": {}, "failed": {}, "unbound": {}},
        custom_mcps={},
    )
    transport = Transport(MCPToolsListProtocolResult(
        MCPToolsListProtocolStatus.SUCCESS_WITH_TOOLS, [{"name": "tool"}],
    ))
    outcomes = discover_catalog_outcomes(desired, {
        "ok": MCPTransportBindingOutcome(MCPTransportBindingStatus.BOUND, transport=transport),
        "disabled": MCPTransportBindingOutcome(MCPTransportBindingStatus.DISABLED),
        "missing": MCPTransportBindingOutcome(MCPTransportBindingStatus.MISSING),
        "failed": MCPTransportBindingOutcome(MCPTransportBindingStatus.CONSTRUCTION_FAILED, diagnostic="boom"),
    })

    assert transport.calls == 1
    assert {key: value.status.name for key, value in outcomes.items()} == {
        "ok": "PROTOCOL_RESULT",
        "disabled": "DISABLED",
        "missing": "TRANSPORT_MISSING",
        "failed": "TRANSPORT_BINDING_FAILED",
        "unbound": "DISCOVERY_NOT_RUN",
    }
    assert outcomes["disabled"].protocol_result is None


def test_discovery_boundary_catches_exceptions_without_fake_p13_result():
    from mcp.catalog_contracts import MCPDesiredState, MCPTransportBindingOutcome, MCPTransportBindingStatus
    from mcp.catalog_discovery import discover_catalog_outcomes

    desired = MCPDesiredState(core_mcps={"bad": {}}, custom_mcps={})
    outcomes = discover_catalog_outcomes(desired, {
        "bad": MCPTransportBindingOutcome(MCPTransportBindingStatus.BOUND, transport=Transport(exc=RuntimeError("x"))),
    })

    assert outcomes["bad"].status.name == "TRANSPORT_BINDING_FAILED"
    assert outcomes["bad"].protocol_result is None
