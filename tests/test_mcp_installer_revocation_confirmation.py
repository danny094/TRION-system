import asyncio
from dataclasses import FrozenInstanceError
import pytest
from fastapi import HTTPException

from mcp.catalog_contracts import (
    CatalogRevocationOutcome,
    MCPDesiredState,
    MCPRegistryReloadConfirmation,
    MCPToolCatalogSnapshot,
)


def _snapshot(custom=None):
    custom = custom or {}
    ids = set(custom)
    return MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState({}, custom),
        {name: None for name in ids},
        {name: None for name in ids},
        {name: {"online": True, "routable": bool(custom[name].get("tools"))} for name in ids},
        {},
        {},
    )


def _confirmation(custom=None):
    return MCPRegistryReloadConfirmation(_snapshot(custom), CatalogRevocationOutcome(0))


def test_confirmation_is_immutable_and_type_checked():
    confirmation = _confirmation({"demo": {"enabled": True}})

    with pytest.raises(FrozenInstanceError):
        confirmation.revocation = CatalogRevocationOutcome(1)
    with pytest.raises(TypeError):
        MCPRegistryReloadConfirmation("not-snapshot", CatalogRevocationOutcome(0))
    with pytest.raises(TypeError):
        MCPRegistryReloadConfirmation(_snapshot(), "not-revocation")


def test_reload_registry_refresh_and_reload_handoff_preserve_identity(monkeypatch):
    import mcp.hub as hub_module
    from mcp.hub import MCPHub
    from mcp.installer_common import reload_hub_registry

    candidate = _snapshot({"demo": {"enabled": True}})
    events = []
    revocation = CatalogRevocationOutcome(2)

    monkeypatch.setattr(hub_module, "build_catalog_snapshot", lambda: events.append("build") or candidate)
    monkeypatch.setattr(
        hub_module,
        "revoke_catalog_routes",
        lambda retire, replacement_snapshot=None: events.append(("revoke", replacement_snapshot)) or revocation,
    )
    monkeypatch.setattr(MCPHub, "_register_tools_in_memory", lambda self: events.append("register"))
    hub = MCPHub()
    hub._initialized = True

    confirmation = hub.reload_registry()
    assert confirmation.published_snapshot is candidate
    assert confirmation.revocation is revocation
    refresh_confirmation = hub.refresh()
    assert refresh_confirmation.published_snapshot is candidate
    assert refresh_confirmation.revocation is revocation
    assert events[:3] == ["build", ("revoke", candidate), "register"]

    fixed = _confirmation({"demo": {"enabled": True}})
    fake_hub = type("Hub", (), {"reload_registry": lambda self: fixed})()
    assert reload_hub_registry(fake_hub) is fixed


@pytest.mark.parametrize("bad", [None, "reload_registry", {"success": True}])
def test_reload_handoff_rejects_legacy_results(bad):
    from mcp.installer_common import InstallationError, reload_hub_registry

    fake_hub = type("Hub", (), {"reload_registry": lambda self: bad})()
    with pytest.raises(InstallationError):
        reload_hub_registry(fake_hub)


def test_postcondition_checks_exact_config_enabled_and_absent():
    from mcp.installer_confirmation import ABSENT, require_registry_postcondition
    from mcp.installer_registry import registry_entry_from_config

    config = {"enabled": True, "transport": "http", "url": "u", "description": "d"}
    confirmation = _confirmation({"demo": registry_entry_from_config(config)})
    require_registry_postcondition(confirmation, "demo", config)
    require_registry_postcondition(
        _confirmation({"demo": registry_entry_from_config({**config, "enabled": False})}),
        "demo",
        {**config, "enabled": False},
    )
    require_registry_postcondition(_confirmation({}), "demo", ABSENT)

    with pytest.raises(ValueError):
        require_registry_postcondition(confirmation, "demo", {**config, "url": "other"})
    with pytest.raises(ValueError):
        require_registry_postcondition(confirmation, "demo", ABSENT)


def test_install_ignores_unhealthy_health_after_confirmed_publication(monkeypatch, tmp_path):
    import mcp.installer_install_routes as routes

    config = {"id": "demo", "display_name": "Demo", "enabled": True, "transport": "http"}
    seen = {}
    async def resolve_upload(file, request):
        return _Upload()

    async def health_check(hub, name):
        return {"status": "unhealthy", "reason": "free text"}

    monkeypatch.setattr(routes, "_resolve_upload", resolve_upload)
    monkeypatch.setattr(routes, "extract_archive", lambda filename, content: (__import__("pathlib").Path("/tmp/unused"), config))
    monkeypatch.setattr(routes, "custom_mcp_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(routes, "custom_mcps_dir", lambda: tmp_path)
    monkeypatch.setattr(routes.shutil, "move", lambda src, dst: None)
    monkeypatch.setattr(routes, "prepare_runtime", lambda target, cfg: {"runtime_kind": "none", "runtime_created_paths": []})
    monkeypatch.setattr(routes, "upsert_registry_entry", lambda name, cfg: seen.setdefault("config", dict(cfg)))
    monkeypatch.setattr(routes, "build_install_receipt", lambda *a, **k: {})
    monkeypatch.setattr(routes, "write_install_receipt", lambda *a: None)
    monkeypatch.setattr(routes, "get_registry_path", lambda: "registry.json")
    monkeypatch.setattr(routes, "get_all_mcps", lambda: {})
    monkeypatch.setattr(routes, "get_hub", lambda: object())
    from mcp.installer_registry import registry_entry_from_config

    monkeypatch.setattr(routes, "reload_hub_registry", lambda hub: _confirmation({"demo": registry_entry_from_config(seen["config"])}))
    monkeypatch.setattr(routes, "run_post_install_health_check", health_check)

    result = asyncio.run(routes.install_mcp(None))

    assert result["success"] is True
    assert result["health"]["status"] == "unhealthy"


def test_cleanup_and_delete_require_confirmed_absence_before_bundle_delete(monkeypatch, tmp_path):
    import mcp.installer_install_routes as install_routes
    import mcp.installer_manage_routes as manage_routes

    target = tmp_path / "demo"
    target.mkdir()
    calls = []
    monkeypatch.setattr(install_routes, "remove_registry_entry", lambda name: None)
    monkeypatch.setattr(install_routes, "get_hub", lambda: object())
    monkeypatch.setattr(install_routes, "reload_hub_registry", lambda hub: _confirmation({"demo": {"enabled": True}}))
    monkeypatch.setattr(install_routes.shutil, "rmtree", lambda path: calls.append(path))
    status = install_routes._cleanup_failed_install("demo", target)
    assert calls == []
    assert status["bundle_removed"] is False

    target.joinpath("mcp.json").write_text("{}", encoding="utf-8")
    target.joinpath(".trion-install.json").write_text('{"mcp_id":"demo","owned_paths":[]}', encoding="utf-8")
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    monkeypatch.setattr(manage_routes, "remove_registry_entry", lambda name: None)
    monkeypatch.setattr(manage_routes, "reload_hub_registry", lambda hub: _confirmation({"demo": {"enabled": True}}))
    with pytest.raises(HTTPException):
        asyncio.run(manage_routes.delete_mcp("demo"))


def test_toggle_and_update_confirm_intended_canonical_config(monkeypatch, tmp_path):
    import mcp.installer_manage_routes as routes
    from mcp.installer_registry import registry_entry_from_config

    path = tmp_path / "mcp.json"
    path.write_text("{}", encoding="utf-8")
    raw = {"id": "demo", "enabled": True, "transport": "http", "url": "u"}
    normalized = {**raw, "enabled": False, "description": "d"}
    seen = []
    monkeypatch.setattr(routes, "is_installer_owned", lambda name: True)
    monkeypatch.setattr(routes, "custom_config_path", lambda name: path)
    monkeypatch.setattr(routes, "load_custom_config", lambda name: dict(raw))
    monkeypatch.setattr(routes, "normalize_manifest_payload", lambda name, config: dict(normalized))
    monkeypatch.setattr(routes, "_validate_manifest_identity", lambda *args: None)
    monkeypatch.setattr(routes, "_preserve_runtime_context", lambda *args: None)
    monkeypatch.setattr(routes, "_preserve_tool_intents", lambda *args: None)
    monkeypatch.setattr(routes, "_apply_config_and_registry_update", lambda name, config, item: seen.append(item))
    monkeypatch.setattr(routes, "reload_hub_registry", lambda hub: _confirmation({"demo": registry_entry_from_config(seen[-1])}))
    assert asyncio.run(routes.toggle_mcp("demo")) == {"success": True, "enabled": False}
    class Request:
        async def json(self):
            return {"config": dict(raw)}

    request = Request()
    assert asyncio.run(routes.update_mcp_config_payload("demo", request))["success"] is True


class _Upload:
    filename = "demo.zip"

    async def read(self):
        return b"bundle"
