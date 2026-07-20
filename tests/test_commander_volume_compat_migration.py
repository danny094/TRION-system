from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = ROOT / "adapters" / "admin-api" / "commander_volume_compat.py"


def test_commander_volume_compat_is_local_truth_for_legacy_namespace():
    source = COMPAT_PATH.read_text(encoding="utf-8")

    assert "def list_volumes(" in source
    assert "def get_volume(" in source
    assert "def remove_volume(" in source
    assert "def find_latest_volume(" in source
    assert "def cleanup_orphaned_volumes(" in source
    assert "def create_snapshot(" in source
    assert "def restore_snapshot(" in source
    assert "def list_snapshots(" in source
    assert "def delete_snapshot(" in source
    assert "from commander_volume_runtime import (" in source
