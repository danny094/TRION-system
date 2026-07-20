from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = ROOT / "adapters" / "admin-api" / "commander_mount_utils.py"
ORCHESTRATOR_PATH = ROOT / "adapters" / "admin-api" / "commander_deploy_orchestrator.py"


def test_local_mount_utils_exposes_bind_mount_truth():
    source = LOCAL_PATH.read_text(encoding="utf-8")

    assert 'os.environ.get("STORAGE_HOST_HELPER_URL", "http://storage-host-helper:8090")' in source
    assert "def _host_helper_mkdirs(" in source
    assert "def ensure_bind_mount_host_dirs(" in source
    assert "storage-host-helper" in source
    assert "os.makedirs(host_abs, mode=0o750, exist_ok=True)" in source


def test_deploy_orchestrator_uses_local_mount_utils_truth():
    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "from commander_mount_utils import ensure_bind_mount_host_dirs" in source
    assert "from mount_utils import ensure_bind_mount_host_dirs" not in source
