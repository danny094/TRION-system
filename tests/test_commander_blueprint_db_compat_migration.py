from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_blueprint_db_compat.py"


def test_commander_blueprint_db_compat_is_local_truth_for_db_init_wrapper():
    source = PATH.read_text(encoding="utf-8")

    assert 'DB_PATH = os.environ.get("COMMANDER_DB_PATH", "/app/data/commander.db")' in source
    assert "from commander_deploy_blueprints import ensure_store_initialized, get_conn as _get_conn" in source
    assert "def init_db():" in source
