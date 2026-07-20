from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = ROOT / "adapters" / "admin-api" / "commander_server_compat.py"


def test_commander_server_compat_is_local_truth_for_legacy_server_wrappers():
    source = COMPAT_PATH.read_text(encoding="utf-8")

    assert "def blueprint_summary(" in source
    assert "def blueprint_detail(" in source
    assert "def deploy_container(" in source
    assert "def stop_container(" in source
    assert "def exec_in_container(" in source
    assert "def blueprint_list(" in source
    assert "def approval_request(" in source
    assert "from commander_container_lifecycle import start_container" in source
    assert "from commander_api.mcp_runtime import stop_container_via_mcp" in source
    assert "from commander_blueprint_write import create_blueprint" in source
    assert "from commander_approval_compat import request_legacy_approval" in source
