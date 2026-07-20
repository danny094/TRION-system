from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "adapters" / "admin-api" / "commander_host_runtime_discovery.py"
POSTCHECKS_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_postchecks.py"


def test_local_host_runtime_discovery_exposes_honest_v2_facade():
    source = RUNTIME_PATH.read_text(encoding="utf-8")

    assert "def run_package_host_runtime_checks(" in source
    assert "host_runtime_requirements_not_implemented_in_v2" in source
    assert '"ok": True' in source


def test_postchecks_use_local_host_runtime_discovery_truth():
    source = POSTCHECKS_PATH.read_text(encoding="utf-8")

    assert "from commander_host_runtime_discovery import run_package_host_runtime_checks" in source
    assert "from host_runtime_discovery import run_package_host_runtime_checks" not in source
