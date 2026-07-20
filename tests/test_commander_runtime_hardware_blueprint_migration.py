from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = ROOT / "adapters" / "admin-api" / "commander_runtime_hardware_blueprint.py"


def test_local_runtime_hardware_blueprint_exposes_seed_truth():
    source = LOCAL_PATH.read_text(encoding="utf-8")

    assert "def _service_source_root(" in source
    assert "def _service_file_map(" in source
    assert "def _load_service_sources(" in source
    assert "def runtime_hardware_dockerfile(" in source
    assert "def ensure_runtime_hardware_blueprint(" in source
    assert "from commander_blueprint_write import create_blueprint, update_blueprint" in source
    assert "from commander_deploy_blueprints import get_blueprint" in source
    assert "from commander_storage_scope_store import upsert_scope" in source
