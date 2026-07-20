from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_blueprint_crud_compat.py"


def test_commander_blueprint_crud_compat_is_local_truth_for_legacy_wrappers():
    source = PATH.read_text(encoding="utf-8")

    assert "def create_blueprint(bp: Any):" in source
    assert "def update_blueprint(blueprint_id: str, updates: dict) -> Optional[Any]:" in source
    assert "def delete_blueprint(blueprint_id: str) -> bool:" in source
    assert "from commander_blueprint_write import create_blueprint as _create_blueprint_dict" in source
    assert "from commander_deploy_blueprints import get_blueprint, list_blueprints" in source
