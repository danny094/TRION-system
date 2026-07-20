from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = ROOT / "adapters" / "admin-api" / "commander_network_compat.py"


def test_commander_network_compat_is_local_truth_for_legacy_namespace():
    source = COMPAT_PATH.read_text(encoding="utf-8")

    assert "def ensure_shared_network(" in source
    assert "def resolve_network(" in source
    assert "def list_networks(" in source
    assert "def remove_network(" in source
    assert "def cleanup_networks(" in source
    assert "def get_network_info(" in source
    assert "from commander_network_runtime import (" in source
    assert "from commander_deploy_container_run import ensure_shared_network as ensure_shared_network_local" in source
    assert "from commander_deploy_container_run import resolve_network as resolve_network_local" in source
