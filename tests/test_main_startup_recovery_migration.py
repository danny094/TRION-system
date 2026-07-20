from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "adapters" / "admin-api" / "main.py"


def test_main_startup_uses_local_recovery_truth():
    source = MAIN.read_text(encoding="utf-8")

    assert "from commander_deploy_runtime_state import recover" in source
    assert "from engine import recover" not in source
