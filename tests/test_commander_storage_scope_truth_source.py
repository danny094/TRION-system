import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_storage_scope_truth_roundtrip_is_local(monkeypatch, tmp_path):
    scopes_path = tmp_path / "storage_scopes.json"
    monkeypatch.setenv("COMMANDER_STORAGE_SCOPES_PATH", str(scopes_path))

    if "commander_storage_scope_store" in sys.modules:
        sys.modules.pop("commander_storage_scope_store")

    truth = _load_module("commander_storage_scope_store")

    stored = truth.upsert_scope(
        "media",
        [{"path": str(tmp_path / "media"), "mode": "ro"}],
        approved_by="test",
        metadata={"owner": "qa"},
    )
    assert stored["name"] == "media"
    assert truth.get_scope("media")["metadata"]["owner"] == "qa"
    assert truth.list_scopes()["media"]["roots"][0]["mode"] == "ro"
    assert truth.delete_scope("media") is True
    assert truth.get_scope("media") is None


def test_storage_route_reads_scopes_from_truth_module():
    source = (ADMIN_API_DIR / "commander_api" / "storage.py").read_text(encoding="utf-8")
    assert "from commander_storage_scope_store import list_scopes" in source
    assert "from commander_storage_scope_store import get_scope" in source
    assert "from commander_storage_scope_store import upsert_scope" in source
    assert "from commander_storage_scope_store import delete_scope" in source
    assert "from container_commander.storage_scope import list_scopes" not in source


def test_deploy_orchestrator_reads_mount_validation_from_truth_module():
    source = (ADMIN_API_DIR / "commander_deploy_orchestrator.py").read_text(encoding="utf-8")
    assert "from commander_storage_scope_store import validate_blueprint_mounts" in source
    assert "from storage_scope import validate_blueprint_mounts" not in source


def test_storage_scope_truth_exposes_storage_provision():
    source = (ADMIN_API_DIR / "commander_storage_scope_store.py").read_text(encoding="utf-8")
    assert "def provision_storage(" in source
    assert 'raise ValueError("path must be absolute")' in source
    assert "os.makedirs(target_path, mode=0o750, exist_ok=True)" in source


def test_vendor_storage_scope_namespace_is_removed():
    assert not (ADMIN_API_DIR / "vendor" / "container_commander" / "storage_scope.py").exists()
