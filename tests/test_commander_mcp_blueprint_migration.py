import asyncio
import importlib
import sys
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _ensure_admin_api_path() -> None:
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))


def _load_module(name: str):
    _ensure_admin_api_path()
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


def test_api_list_blueprints_uses_mcp_helper(monkeypatch):
    routes = _load_module("commander_routes")
    monkeypatch.setattr(
        routes,
        "list_blueprints_via_mcp",
        lambda: [{"blueprint_id": "bp1", "name": "Demo", "description": "", "version": "v1"}],
    )

    data = asyncio.run(routes.api_list_blueprints())

    assert data["count"] == 1
    assert data["blueprints"][0]["blueprint_id"] == "bp1"


def test_api_list_blueprints_filters_by_tag_via_detail_reads(monkeypatch):
    routes = _load_module("commander_routes")
    monkeypatch.setattr(
        routes,
        "list_blueprints_via_mcp",
        lambda: [
            {"blueprint_id": "bp1", "name": "Demo", "description": "", "version": "v1"},
            {"blueprint_id": "bp2", "name": "Other", "description": "", "version": "v2"},
        ],
    )

    def fake_get_blueprint(blueprint_id: str):
        if blueprint_id == "bp1":
            return {"blueprint_id": "bp1", "definition": {"tags": ["gpu", "desktop"]}}
        return {"blueprint_id": "bp2", "definition": {"tags": ["cpu"]}}

    monkeypatch.setattr(routes, "get_blueprint_via_mcp", fake_get_blueprint)

    data = asyncio.run(routes.api_list_blueprints(tag="gpu"))

    assert data["count"] == 1
    assert data["blueprints"][0]["blueprint_id"] == "bp1"


def test_api_get_blueprint_uses_mcp_helper(monkeypatch):
    routes = _load_module("commander_routes")
    monkeypatch.setattr(
        routes,
        "get_blueprint_via_mcp",
        lambda blueprint_id: {
            "blueprint_id": blueprint_id,
            "name": "Demo",
            "description": "",
            "version": "v1",
            "definition": {"dockerfile": "FROM python:3.12"},
        },
    )

    data = asyncio.run(routes.api_get_blueprint("bp1"))

    assert data["blueprint_id"] == "bp1"
    assert data["definition"]["dockerfile"] == "FROM python:3.12"


def test_api_get_blueprint_hardware_preview_degrades_honestly(monkeypatch):
    routes = _load_module("commander_routes")
    monkeypatch.setattr(
        routes,
        "get_blueprint_via_mcp",
        lambda blueprint_id: {
            "blueprint_id": blueprint_id,
            "name": "Demo",
            "description": "",
            "version": "v1",
            "definition": {},
        },
    )

    data = asyncio.run(routes.api_get_blueprint("bp1", hardware_preview=True))

    assert data["hardware_preview"]["available"] is False
    assert data["hardware_preview"]["target_id"] == "bp1"
    assert data["hardware_preview_error"] == "hardware_preview_unavailable_in_blueprint_read_v2"


def test_blueprint_read_slice_no_longer_uses_direct_legacy_imports():
    source = (ADMIN_API_DIR / "commander_routes.py").read_text()

    assert "from container_commander.store import list_blueprints" not in source
    assert "from container_commander.store import resolve_blueprint" not in source
    assert "from container_commander.store import get_blueprint" not in source
