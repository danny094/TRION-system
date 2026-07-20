from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = ROOT / "adapters" / "admin-api" / "commander_port_manager.py"
SUPPORT_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_support.py"
RUN_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_container_run.py"


def test_local_port_manager_exposes_port_truth():
    source = LOCAL_PATH.read_text(encoding="utf-8")

    assert "def list_used_ports(" in source
    assert "def check_port(" in source
    assert "def find_free_port(" in source
    assert "def validate_port_bindings(" in source
    assert "def list_blueprint_ports(" in source
    assert "socket.SOCK_DGRAM" in source
    assert 'filters={"label": "trion.managed=true"}' in source


def test_active_deploy_modules_use_local_port_manager_truth():
    support_source = SUPPORT_PATH.read_text(encoding="utf-8")
    run_source = RUN_PATH.read_text(encoding="utf-8")

    assert "from commander_port_manager import find_free_port" in support_source
    assert "from port_manager import find_free_port" not in support_source

    assert "from commander_port_manager import validate_port_bindings" in run_source
    assert "from port_manager import validate_port_bindings" not in run_source
