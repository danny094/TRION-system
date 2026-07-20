import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_commander_secret_store_uses_scoped_namespaces(monkeypatch):
    store = _load_module("commander_secret_store")
    captured: list[tuple[str, dict]] = []

    def fake_call(tool: str, args: dict):
        captured.append((tool, dict(args)))
        if tool == "secret_list":
            return {
                "secrets": [
                    "CC_GLOBAL::OPENAI_API_KEY",
                    "CC_BLUEPRINT::bp-1::STEAM_TOKEN",
                    "UNRELATED_SECRET",
                ]
            }
        if tool == "secret_save":
            return {"success": True}
        if tool == "secret_get":
            if args["name"] == "CC_BLUEPRINT::bp-1::STEAM_TOKEN":
                return {"value": "blueprint-secret"}
            if args["name"] == "CC_GLOBAL::OPENAI_API_KEY":
                return {"value": "global-secret"}
            return {"value": None}
        if tool == "secret_delete":
            return {"success": True}
        raise AssertionError(tool)

    monkeypatch.setattr(store, "_mcp_call", fake_call)

    entries = store.list_secrets()
    assert [entry.name for entry in entries] == ["OPENAI_API_KEY", "STEAM_TOKEN"]
    assert entries[0].scope.value == "global"
    assert entries[1].scope.value == "blueprint"
    assert entries[1].blueprint_id == "bp-1"

    saved = store.store_secret("steam_token", "abc", entries[1].scope, "bp-1")
    assert saved.name == "STEAM_TOKEN"
    assert captured[-1] == ("secret_save", {"name": "CC_BLUEPRINT::bp-1::STEAM_TOKEN", "value": "abc"})

    env = store.get_secrets_for_blueprint(
        "bp-1",
        [{"name": "steam_token", "optional": False}, {"name": "openai_api_key", "optional": False}],
    )
    assert env == {"STEAM_TOKEN": "blueprint-secret", "OPENAI_API_KEY": "global-secret"}

    deleted = store.delete_secret("openai_api_key", entries[0].scope)
    assert deleted is True
    assert captured[-1] == ("secret_delete", {"name": "CC_GLOBAL::OPENAI_API_KEY"})


def test_commander_secret_routes_use_truth_module():
    secrets_source = (ADMIN_API_DIR / "commander_api" / "secrets.py").read_text(encoding="utf-8")
    audit_source = (ADMIN_API_DIR / "commander_api" / "audit.py").read_text(encoding="utf-8")
    assert "from commander_secret_store import list_secrets" in secrets_source
    assert "from commander_secret_store import store_secret" in secrets_source
    assert "from commander_secret_store import delete_secret" in secrets_source
    assert "from commander_secret_store import get_access_log" in audit_source
    assert "from container_commander.secret_store import list_secrets" not in secrets_source


def test_vendor_secret_store_namespace_is_removed():
    assert not (ADMIN_API_DIR / "vendor" / "container_commander" / "secret_store.py").exists()
