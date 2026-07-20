from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "adapters" / "admin-api" / "commander_blueprint_seeds.py"


def test_local_blueprint_seeds_uses_local_truths():
    source = LOCAL.read_text(encoding="utf-8")

    assert "from commander_blueprint_trust import OFFICIAL_BLUEPRINT_IDS" in source
    assert "from commander_blueprint_write import create_blueprint" in source
    assert "from commander_deploy_blueprints import ensure_store_initialized, get_conn" in source
    assert "from store.crud import create_blueprint, get_active_blueprint_ids" not in source
    assert "from store.db import _get_conn, ensure_store_initialized" not in source
