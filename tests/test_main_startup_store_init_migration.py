from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "adapters" / "admin-api" / "main.py"


def test_main_startup_uses_local_store_init_truth():
    source = MAIN.read_text()

    assert "from commander_deploy_blueprints import ensure_store_initialized" in source
    assert "from store.db import ensure_store_initialized" not in source
