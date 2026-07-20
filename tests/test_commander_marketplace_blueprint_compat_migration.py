from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = ROOT / "adapters" / "admin-api" / "commander_marketplace_blueprint_compat.py"


def test_commander_marketplace_blueprint_compat_is_local_truth():
    source = COMPAT_PATH.read_text(encoding="utf-8")

    assert "def get_blueprint_local(" in source
    assert "def resolve_blueprint_local(" in source
    assert "def create_blueprint_local(" in source
    assert "def update_blueprint_local(" in source
    assert "from commander_deploy_blueprints import get_blueprint" in source
    assert "from commander_deploy_blueprints import resolve_blueprint" in source
    assert "from commander_blueprint_write import create_blueprint" in source
    assert "from commander_blueprint_write import update_blueprint" in source
