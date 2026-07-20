from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINTS_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_blueprints.py"
RUNTIME_CLIENT_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_runtime_client.py"
ORCHESTRATOR_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_orchestrator.py"


def test_active_deploy_modules_no_longer_inject_vendor_package_root():
    blueprints_source = BLUEPRINTS_PATH.read_text(encoding="utf-8")
    runtime_client_source = RUNTIME_CLIENT_PATH.read_text(encoding="utf-8")
    orchestrator_source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "_VENDOR_PACKAGE_ROOT" not in blueprints_source
    assert "sys.path.insert" not in blueprints_source
    assert "from models import Blueprint" in blueprints_source

    assert "_VENDOR_PACKAGE_ROOT" not in runtime_client_source
    assert "sys.path.insert" not in runtime_client_source

    assert "_VENDOR_PACKAGE_ROOT" not in orchestrator_source
    assert "sys.path.insert" not in orchestrator_source
