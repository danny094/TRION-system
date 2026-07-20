import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"
VENDOR_PACKAGE_DIR = VENDOR_DIR / "container_commander"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    if str(VENDOR_PACKAGE_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_PACKAGE_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_approval_compat_delegates_to_local_request(monkeypatch):
    compat = _load_module("commander_approval_compat")

    class _Pending:
        def to_dict(self):
            return {"id": "a1", "status": "pending"}

    monkeypatch.setattr(compat, "request_approval", lambda **kwargs: _Pending(), raising=False)

    result = compat.request_legacy_approval(
        "deploy",
        {"blueprint_id": "bp1", "reason": "Need approval", "network_mode": "bridge"},
    )

    assert result == {"id": "a1", "status": "pending"}


def test_blueprint_write_module_exists_and_no_vendor_store_imports():
    source = (ADMIN_API_DIR / "commander_blueprint_write.py").read_text()

    assert "from commander_deploy_blueprints import ensure_store_initialized, get_blueprint, get_conn" in source
    assert "from store import" not in source
    assert "from store.crud import" not in source
