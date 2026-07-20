import asyncio
import importlib
import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_network_read_routes_use_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(
        storage,
        "list_networks_via_mcp",
        lambda: [{"name": "trion-sandbox", "type": "internal"}],
    )
    monkeypatch.setattr(
        storage,
        "get_network_info_via_mcp",
        lambda container_id: {"trion-sandbox": {"ip": "172.20.0.2"}},
    )

    listed = asyncio.run(storage.api_list_networks())
    detail = asyncio.run(storage.api_network_info("c1"))

    assert listed == {"networks": [{"name": "trion-sandbox", "type": "internal"}], "count": 1}
    assert detail == {"container_id": "c1", "networks": {"trion-sandbox": {"ip": "172.20.0.2"}}}


def test_network_cleanup_route_uses_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(storage, "cleanup_networks_via_mcp", lambda: ["trion-iso-empty"])

    payload = asyncio.run(storage.api_cleanup_networks())
    assert payload == {"removed": ["trion-iso-empty"], "count": 1}


def test_network_read_slice_no_longer_uses_vendor_imports():
    storage = _load_module("commander_api.storage")
    list_source = inspect.getsource(storage.api_list_networks)
    info_source = inspect.getsource(storage.api_network_info)
    cleanup_source = inspect.getsource(storage.api_cleanup_networks)
    assert "container_commander.network" not in list_source
    assert "container_commander.network" not in info_source
    assert "container_commander.network" not in cleanup_source
    assert "list_networks_via_mcp" in list_source
    assert "get_network_info_via_mcp" in info_source
    assert "cleanup_networks_via_mcp" in cleanup_source
