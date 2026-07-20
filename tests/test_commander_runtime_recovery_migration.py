import importlib
import sys
from pathlib import Path
from types import SimpleNamespace


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


def test_runtime_recovery_helpers_exist_in_local_state():
    state = _load_module("commander_deploy_runtime_state")
    source = (ADMIN_API_DIR / "commander_deploy_runtime_state.py").read_text()

    assert "def update_quota_used()" in source
    assert "def recover() -> dict[str, Any]:" in source
    assert callable(state.update_quota_used)
    assert callable(state.recover)


def test_runtime_update_quota_used_operates_on_local_state(monkeypatch):
    state = _load_module("commander_deploy_runtime_state")
    runtime_models = _load_module("commander_runtime_models")

    monkeypatch.setattr(
        state,
        "_quota",
        runtime_models.SessionQuota(
            max_containers=5,
            max_total_memory_mb=2048,
            max_total_cpu=4.0,
            containers_used=0,
            memory_used_mb=0,
            cpu_used=0.0,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        state,
        "_active",
        {
            "c1": SimpleNamespace(memory_limit_mb=256.0, cpu_limit_alloc=1.5),
            "c2": SimpleNamespace(memory_limit_mb=512.0, cpu_limit_alloc=0.5),
        },
        raising=False,
    )

    state.update_quota_used()

    assert state._quota.containers_used == 2
    assert state._quota.memory_used_mb == 768.0
    assert state._quota.cpu_used == 2.0
