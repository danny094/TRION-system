from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = ROOT / "adapters" / "admin-api" / "commander_runtime_start_compat.py"


def test_commander_runtime_start_compat_is_local_truth():
    source = COMPAT_PATH.read_text(encoding="utf-8")

    assert "def start_container(" in source
    assert "from commander_deploy_orchestrator import start_container as orchestrate_start_container" in source
    assert "from commander_runtime_errors import PendingApprovalError" in source
