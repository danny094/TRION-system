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


def test_storage_managed_paths_uses_storage_broker_only(monkeypatch):
    storage = _load_module("commander_api.storage")

    async def fake_mcp_call(tool_name: str):
        assert tool_name == "storage_list_managed_paths"
        return {"managed_paths": ["/srv/data", "/srv/data", "/mnt/archive"]}

    import storage_broker_routes

    monkeypatch.setattr(storage_broker_routes, "_mcp_call", fake_mcp_call)

    payload = asyncio.run(storage.api_list_storage_managed_paths())
    assert payload == {
        "managed_paths": ["/mnt/archive", "/srv/data"],
        "catalog": [
            {
                "id": "mp:archive:2",
                "label": "archive",
                "path": "/mnt/archive",
                "source": "storage_broker",
            },
            {
                "id": "mp:data:1",
                "label": "data",
                "path": "/srv/data",
                "source": "storage_broker",
            },
        ],
        "count": 2,
    }


def test_storage_managed_paths_slice_has_no_vendor_enrichment():
    storage = _load_module("commander_api.storage")
    source = inspect.getsource(storage.api_list_storage_managed_paths)
    assert "_extend_catalog_with_scopes" not in source
    assert "_extend_catalog_with_assets" not in source
    assert "container_commander.storage_scope" not in source
    assert "container_commander.storage_assets" not in source
