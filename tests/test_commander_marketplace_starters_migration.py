from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STARTERS_PATH = ROOT / "adapters" / "admin-api" / "commander_marketplace_starters.py"


def test_commander_marketplace_starters_is_local_truth_for_starters():
    source = STARTERS_PATH.read_text(encoding="utf-8")

    assert "STARTER_BLUEPRINTS = [" in source
    assert '\"python-sandbox\"' in source
    assert "def get_starters(" in source
    assert "def install_starter(" in source
    assert "from commander_blueprint_write import create_blueprint" in source
    assert "from commander_deploy_blueprints import get_blueprint" in source
