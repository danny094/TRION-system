from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = ROOT / "adapters" / "admin-api" / "commander_runtime_hardware_client.py"
DEPLOY_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_hardware.py"


def test_local_runtime_hardware_client_exposes_full_truth():
    source = LOCAL_PATH.read_text(encoding="utf-8")

    assert "def runtime_hardware_base_urls(" in source
    assert "def request_runtime_hardware(" in source
    assert "def runtime_hardware_support_dir(" in source
    assert "def runtime_hardware_has_host_visibility(" in source
    assert "def should_prefer_local_runtime_hardware(" in source
    assert "def request_local_runtime_hardware_fallback(" in source
    assert "candidate_service_endpoints" in source
    assert "ContainerConnector" in source
    assert "AttachmentIntent" in source
    assert "from commander_storage_assets_store import list_assets" in source
    assert "from storage_assets import list_assets" not in source


def test_deploy_hardware_uses_local_runtime_hardware_client_truth():
    source = DEPLOY_PATH.read_text(encoding="utf-8")

    assert "from commander_runtime_hardware_client import (" in source
    assert "request_runtime_hardware" in source
    assert "request_local_runtime_hardware_fallback" in source
    assert "should_prefer_local_runtime_hardware" in source
    assert "def request_runtime_hardware(" not in source
    assert "def _runtime_hardware_base_urls(" not in source
