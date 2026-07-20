import asyncio
import importlib
import sys
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    for module_name in (
        "commander_api.secrets",
        "commander_api.audit",
        "commander_api.hardware",
        "commander_api.storage",
        "commander_api.operations",
        "trion_memory_routes",
    ):
        stub = ModuleType(module_name)
        stub.router = APIRouter()
        sys.modules[module_name] = stub
    module = importlib.import_module(name)
    return importlib.reload(module)


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_api_create_blueprint_uses_mcp(monkeypatch):
    routes = _load_module("commander_routes")
    monkeypatch.setattr(
        routes,
        "create_blueprint_via_mcp",
        lambda payload: {"blueprint": {"blueprint_id": "bp1"}, "trust": {"level": "unverified"}},
    )

    data = asyncio.run(routes.api_create_blueprint(_FakeRequest({"id": "bp1", "name": "Demo"})))
    assert data["created"] is True
    assert data["blueprint"]["blueprint_id"] == "bp1"
    assert data["graph_sync"]["attempted"] is False


def test_api_update_delete_import_export_blueprint_use_mcp(monkeypatch):
    routes = _load_module("commander_routes")
    monkeypatch.setattr(
        routes,
        "update_blueprint_via_mcp",
        lambda blueprint_id, updates: {"blueprint": {"blueprint_id": blueprint_id}, "trust": {"level": "verified"}},
    )
    monkeypatch.setattr(routes, "delete_blueprint_via_mcp", lambda blueprint_id: {"deleted": True, "blueprint_id": blueprint_id})
    monkeypatch.setattr(
        routes,
        "import_blueprint_yaml_via_mcp",
        lambda yaml_content: {"blueprint": {"blueprint_id": "bp2"}, "trust": {"level": "unverified"}},
    )
    monkeypatch.setattr(routes, "export_blueprint_yaml_via_mcp", lambda blueprint_id: {"yaml": "id: bp1\nname: Demo\n"})

    updated = asyncio.run(routes.api_update_blueprint("bp1", _FakeRequest({"description": "x"})))
    deleted = asyncio.run(routes.api_delete_blueprint("bp1"))
    imported = asyncio.run(routes.api_import_blueprint(_FakeRequest({"yaml": "id: bp2\nname: Demo\n"})))
    exported = asyncio.run(routes.api_export_yaml("bp1"))

    assert updated["updated"] is True
    assert deleted["deleted"] is True
    assert imported["imported"] is True
    assert exported["yaml"].startswith("id: bp1")


def test_blueprint_write_slice_no_longer_uses_direct_legacy_imports():
    source = (ADMIN_API_DIR / "commander_routes.py").read_text()
    assert "from container_commander.store import create_blueprint" not in source
    assert "from container_commander.store import update_blueprint" not in source
    assert "from container_commander.store import delete_blueprint" not in source
    assert "from container_commander.store import import_from_yaml" not in source
    assert "from container_commander.store import export_to_yaml" not in source
