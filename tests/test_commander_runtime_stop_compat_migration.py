from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_runtime_stop_compat.py"


def test_commander_runtime_stop_compat_is_local_truth_for_stop_wrappers():
    source = PATH.read_text(encoding="utf-8")

    assert "from commander_api.mcp_runtime import start_container_via_mcp, stop_container_via_mcp" in source
    assert "from commander_container_lifecycle import remove_stopped_container as remove_stopped_container_local" in source
    assert "def stop_container(container_id: str, remove=None) -> bool:" in source
    assert "def remove_stopped_container(container_id: str) -> dict:" in source
    assert "def start_stopped_container(container_id: str) -> bool:" in source
