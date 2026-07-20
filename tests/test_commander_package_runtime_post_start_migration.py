from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = ROOT / "adapters" / "admin-api" / "commander_package_runtime_post_start.py"
POSTCHECKS_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_postchecks.py"


def test_local_package_runtime_post_start_exposes_runtime_post_start_truth():
    source = LOCAL_PATH.read_text(encoding="utf-8")

    assert "def _exec_shell(" in source
    assert "def _sync_filestash_connections(" in source
    assert "def run_package_runtime_post_start(" in source
    assert "from commander_package_runtime_views import _filestash_connections_payload, _list_broker_assets" in source
    assert 'general["secret_key"] = "trion-filestash"' in source


def test_deploy_postchecks_use_local_package_runtime_post_start_truth():
    source = POSTCHECKS_PATH.read_text(encoding="utf-8")

    assert "from commander_package_runtime_post_start import run_package_runtime_post_start" in source
    assert "from package_runtime_post_start import run_package_runtime_post_start" not in source
