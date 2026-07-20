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


def test_vendor_volume_read_and_snapshot_paths_delegate_to_mcp(monkeypatch):
    compat = _load_module("commander_volume_compat")

    monkeypatch.setattr(
        compat,
        "list_volumes_via_mcp",
        lambda blueprint_id="": [{"name": "trion_ws_demo_1", "blueprint_id": blueprint_id or "demo"}],
    )
    monkeypatch.setattr(
        compat,
        "get_volume_via_mcp",
        lambda volume_name: {"name": volume_name, "snapshots": [{"filename": "snap.tar.gz"}]},
    )
    monkeypatch.setattr(
        compat,
        "list_snapshots_via_mcp",
        lambda volume_name="": [{"filename": "snap.tar.gz", "volume_name": volume_name}],
    )
    monkeypatch.setattr(compat, "create_snapshot_via_mcp", lambda volume_name, tag="": "snap.tar.gz")
    monkeypatch.setattr(compat, "restore_snapshot_via_mcp", lambda filename, target_volume="": "trion_ws_restored")
    monkeypatch.setattr(compat, "delete_snapshot_via_mcp", lambda filename: True)
    monkeypatch.setattr(compat, "remove_volume_via_mcp", lambda volume_name, force=False: True)
    monkeypatch.setattr(compat, "cleanup_orphaned_volumes_via_mcp", lambda dry_run=True: ["trion_ws_orphan"])

    assert compat.list_volumes("demo") == [{"name": "trion_ws_demo_1", "blueprint_id": "demo"}]
    assert compat.get_volume("trion_ws_demo_1") == {
        "name": "trion_ws_demo_1",
        "snapshots": [{"filename": "snap.tar.gz"}],
    }
    assert compat.list_snapshots("trion_ws_demo_1") == [
        {"filename": "snap.tar.gz", "volume_name": "trion_ws_demo_1"}
    ]
    assert compat.create_snapshot("trion_ws_demo_1", tag="nightly") == "snap.tar.gz"
    assert compat.restore_snapshot("snap.tar.gz", target_volume="trion_ws_restored") == "trion_ws_restored"
    assert compat.delete_snapshot("snap.tar.gz") is True
    assert compat.remove_volume("trion_ws_demo_1", force=True) is True
    assert compat.cleanup_orphaned_volumes(dry_run=False) == ["trion_ws_orphan"]


def test_vendor_volume_find_latest_volume_uses_sorted_mcp_list(monkeypatch):
    compat = _load_module("commander_volume_compat")
    monkeypatch.setattr(
        compat,
        "list_volumes_via_mcp",
        lambda blueprint_id="": [
            {"name": "trion_ws_demo_new", "blueprint_id": blueprint_id},
            {"name": "trion_ws_demo_old", "blueprint_id": blueprint_id},
        ],
    )
    assert compat.find_latest_volume("demo") == "trion_ws_demo_new"
