from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_network_runtime.py"


def test_commander_network_runtime_is_local_truth_for_network_helpers():
    source = PATH.read_text(encoding="utf-8")

    assert "def create_isolated_network(" in source
    assert "def remove_network(" in source
    assert "def list_networks(" in source
    assert "def cleanup_networks(" in source
    assert "def get_network_info(" in source
    assert 'net_name = f"trion-iso-{container_name}"' in source
    assert "list_networks_via_mcp" in source
    assert "get_network_info_via_mcp" in source
    assert "cleanup_networks_via_mcp" in source
    assert "from commander_deploy_container_run import ensure_shared_network, resolve_network" in source
    assert "container_commander.network" not in source
