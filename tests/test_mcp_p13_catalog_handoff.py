import pytest

from mcp.catalog_contracts import CatalogRevocationOutcome, MCPDesiredState, MCPRegistryReloadConfirmation, MCPToolCatalogSnapshot
from mcp.protocol_contracts import MCPToolsListProtocolResult, MCPToolsListProtocolStatus


def test_p13_protocol_success_empty_is_not_installer_confirmation():
    from mcp.installer_common import InstallationError, reload_hub_registry

    p13_result = MCPToolsListProtocolResult(MCPToolsListProtocolStatus.SUCCESS_EMPTY)
    hub = type("Hub", (), {"reload_registry": lambda self: p13_result})()

    with pytest.raises(InstallationError):
        reload_hub_registry(hub)


def test_postcondition_does_not_use_p13_result_or_availability():
    from mcp.installer_confirmation import require_registry_postcondition

    snapshot = MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState({}, {"demo": {"enabled": True}}),
        {"demo": None},
        {"demo": None},
        {"demo": {"online": True, "routable": True, "status": MCPToolsListProtocolStatus.SUCCESS_EMPTY.name}},
        {},
        {},
    )
    confirmation = MCPRegistryReloadConfirmation(snapshot, CatalogRevocationOutcome(0))

    with pytest.raises(ValueError):
        require_registry_postcondition(confirmation, "demo", {"enabled": True, "url": "missing"})
