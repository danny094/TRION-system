from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "adapters" / "admin-api" / "commander_host_companion_runtime.py"
START_ENV_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_start_env.py"
POSTCHECKS_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_postchecks.py"


def test_local_host_companion_runtime_exposes_manifest_and_postcheck_facades():
    source = RUNTIME_PATH.read_text(encoding="utf-8")

    assert "def get_package_manifest(" in source
    assert "def ensure_host_companion(" in source
    assert "def ensure_package_storage_scope(" in source
    assert "def run_package_postchecks(" in source
    assert "repair_host_companion_via_mcp" in source
    assert "package_storage_scope_runtime_not_implemented_in_v2" in source
    assert "package_postchecks_runtime_not_implemented_in_v2" in source


def test_start_env_and_postchecks_use_local_host_companion_runtime_truth():
    start_env = START_ENV_PATH.read_text(encoding="utf-8")
    postchecks = POSTCHECKS_PATH.read_text(encoding="utf-8")

    assert "from commander_host_companion_runtime import (" in start_env
    assert "ensure_host_companion" in start_env
    assert "ensure_package_storage_scope" in start_env
    assert "get_package_manifest" in start_env
    assert "from host_companions import" not in start_env

    assert "from commander_host_companion_runtime import run_package_postchecks" in postchecks
    assert "from host_companions import run_package_postchecks" not in postchecks
