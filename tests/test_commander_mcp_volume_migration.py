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


def test_volume_read_routes_use_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(
        storage,
        "list_volumes_via_mcp",
        lambda blueprint_id="": [{"name": "trion_ws_demo_1", "blueprint_id": "demo"}],
    )
    monkeypatch.setattr(
        storage,
        "get_volume_via_mcp",
        lambda volume_name: {"name": volume_name, "snapshots": [{"filename": "snap.tar.gz"}]},
    )
    monkeypatch.setattr(
        storage,
        "list_snapshots_via_mcp",
        lambda volume_name="": [{"filename": "snap.tar.gz"}],
    )

    listed = asyncio.run(storage.api_list_volumes())
    detail = asyncio.run(storage.api_get_volume("trion_ws_demo_1"))
    snapshots = asyncio.run(storage.api_list_snapshots())

    assert listed == {"volumes": [{"name": "trion_ws_demo_1", "blueprint_id": "demo"}], "count": 1}
    assert detail == {"volume": {"name": "trion_ws_demo_1", "snapshots": [{"filename": "snap.tar.gz"}]}}
    assert snapshots == {"snapshots": [{"filename": "snap.tar.gz"}], "count": 1}


def test_volume_remove_route_uses_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(storage, "remove_volume_via_mcp", lambda volume_name, force=False: True)

    payload = asyncio.run(storage.api_remove_volume("trion_ws_demo_1", force=True))
    assert payload == {"removed": True, "volume": "trion_ws_demo_1"}


def test_volume_cleanup_route_uses_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(storage, "cleanup_orphaned_volumes_via_mcp", lambda dry_run=True: ["trion_ws_orphan"])

    payload = asyncio.run(storage.api_cleanup_volumes(dry_run=False))
    assert payload == {"orphaned": ["trion_ws_orphan"], "count": 1, "dry_run": False}


def test_snapshot_delete_route_uses_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(storage, "delete_snapshot_via_mcp", lambda filename: True)

    payload = asyncio.run(storage.api_delete_snapshot("snap.tar.gz"))
    assert payload == {"deleted": True, "filename": "snap.tar.gz"}


def test_snapshot_create_route_uses_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(storage, "create_snapshot_via_mcp", lambda volume_name, tag="": "snap.tar.gz")

    async def _run():
        class _Request:
            async def json(self):
                return {"volume_name": "trion_ws_demo_1", "tag": "nightly"}

        return await storage.api_create_snapshot(_Request())

    payload = asyncio.run(_run())
    assert payload == {"created": True, "filename": "snap.tar.gz"}


def test_snapshot_restore_route_uses_mcp_runtime(monkeypatch):
    storage = _load_module("commander_api.storage")
    monkeypatch.setattr(storage, "restore_snapshot_via_mcp", lambda filename, target_volume="": "trion_ws_restored")

    async def _run():
        class _Request:
            async def json(self):
                return {"filename": "snap.tar.gz", "target_volume": "trion_ws_restored"}

        return await storage.api_restore_snapshot(_Request())

    payload = asyncio.run(_run())
    assert payload == {"restored": True, "volume": "trion_ws_restored"}


def test_volume_read_slice_no_longer_uses_vendor_imports():
    storage = _load_module("commander_api.storage")
    list_source = inspect.getsource(storage.api_list_volumes)
    get_source = inspect.getsource(storage.api_get_volume)
    snapshots_source = inspect.getsource(storage.api_list_snapshots)
    create_snapshot_source = inspect.getsource(storage.api_create_snapshot)
    restore_snapshot_source = inspect.getsource(storage.api_restore_snapshot)
    delete_snapshot_source = inspect.getsource(storage.api_delete_snapshot)
    remove_source = inspect.getsource(storage.api_remove_volume)
    cleanup_source = inspect.getsource(storage.api_cleanup_volumes)
    combined = "\n".join([list_source, get_source, snapshots_source, create_snapshot_source, restore_snapshot_source, delete_snapshot_source, remove_source, cleanup_source])
    assert "container_commander.volumes" not in combined
    assert "list_volumes_via_mcp" in list_source
    assert "get_volume_via_mcp" in get_source
    assert "list_snapshots_via_mcp" in snapshots_source
    assert "create_snapshot_via_mcp" in create_snapshot_source
    assert "restore_snapshot_via_mcp" in restore_snapshot_source
    assert "delete_snapshot_via_mcp" in delete_snapshot_source
    assert "remove_volume_via_mcp" in remove_source
    assert "cleanup_orphaned_volumes_via_mcp" in cleanup_source
