from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = ROOT / "adapters" / "admin-api" / "commander_volume_runtime.py"


def test_local_volume_runtime_exposes_volume_truth():
    source = LOCAL_PATH.read_text(encoding="utf-8")

    assert "def create_volume(" in source
    assert "def find_latest_volume(" in source
    assert "def create_snapshot(" in source
    assert "def restore_snapshot(" in source
    assert "def delete_snapshot(" in source
    assert 'name = f"trion_ws_{blueprint_id}_{ts}"' in source
    assert "list_volumes_via_mcp" in source
    assert "get_volume_via_mcp" in source
