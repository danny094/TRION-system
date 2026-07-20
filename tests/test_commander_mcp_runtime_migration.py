import asyncio
import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _ensure_admin_api_path() -> None:
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))


def _load_module(name: str):
    _ensure_admin_api_path()
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_evaluate_home_status_via_mcp_returns_home_scope_data(monkeypatch):
    mcp_runtime = _load_module("commander_api.mcp_runtime")

    monkeypatch.setattr(
        mcp_runtime,
        "list_containers_via_mcp",
        lambda timeout=5.0: [
            {"container_id": "c1", "name": "trion-home", "status": "running"},
            {"container_id": "c2", "name": "other", "status": "exited"},
        ],
    )
    monkeypatch.setattr(
        mcp_runtime,
        "inspect_container_via_mcp",
        lambda container_id, timeout=5.0: {
            "container_id": container_id,
            "status": "running",
            "home_scope": {"is_home": True, "home_root": "/home/trion"},
        },
    )

    status = mcp_runtime.evaluate_home_status_via_mcp()

    assert status == {
        "status": "running",
        "error_code": "",
        "home_container_id": "c1",
        "identity_path": "/home/trion",
    }


def test_evaluate_home_status_via_mcp_returns_offline_when_missing(monkeypatch):
    mcp_runtime = _load_module("commander_api.mcp_runtime")
    monkeypatch.setattr(mcp_runtime, "list_containers_via_mcp", lambda timeout=5.0: [])

    status = mcp_runtime.evaluate_home_status_via_mcp()

    assert status == {"status": "offline", "error_code": "home_not_found"}


def test_api_list_containers_uses_mcp_runtime_helper(monkeypatch):
    containers = _load_module("commander_api.containers")
    monkeypatch.setattr(
        containers,
        "list_containers_via_mcp",
        lambda: [{"container_id": "c1", "name": "demo", "status": "running"}],
    )

    data = asyncio.run(containers.api_list_containers())

    assert data["count"] == 1
    assert data["containers"][0]["container_id"] == "c1"


def test_api_home_status_uses_mcp_runtime_helper(monkeypatch):
    containers = _load_module("commander_api.containers")
    monkeypatch.setattr(
        containers,
        "evaluate_home_status_via_mcp",
        lambda: {"status": "running", "error_code": "", "home_container_id": "c1", "identity_path": "/home/trion"},
    )

    data = asyncio.run(containers.api_home_status())

    assert data["status"] == "running"
    assert data["home_container_id"] == "c1"


def test_api_start_and_stop_container_use_mcp_runtime_helper(monkeypatch):
    containers = _load_module("commander_api.containers")

    monkeypatch.setattr(
        containers,
        "start_container_via_mcp",
        lambda container_id: {"action": "started", "container": {"container_id": container_id}},
    )
    monkeypatch.setattr(
        containers,
        "stop_container_via_mcp",
        lambda container_id: {"action": "stopped", "container": {"container_id": container_id}},
    )

    started = asyncio.run(containers.api_start_existing_container("c1"))
    stopped = asyncio.run(containers.api_stop_container("c1"))

    assert started["started"] is True
    assert started["action"] == "started"
    assert stopped["stopped"] is True
    assert stopped["action"] == "stopped"


def test_api_container_logs_normalizes_mcp_result(monkeypatch):
    containers = _load_module("commander_api.containers")
    monkeypatch.setattr(
        containers,
        "get_container_logs_via_mcp",
        lambda container_id, tail=100: {
            "container_id": container_id,
            "logs": "hello",
            "truncated": True,
            "tail": tail,
            "since": "",
            "limit_chars": 16000,
        },
    )

    data = asyncio.run(containers.api_container_logs("c1", tail=120))

    assert data["container_id"] == "c1"
    assert data["logs"] == "hello"
    assert data["truncated"] is True
    assert data["tail"] == 120


def test_runtime_slice_no_longer_uses_direct_legacy_imports():
    runtime_source = (ADMIN_API_DIR / "runtime_routes.py").read_text()
    containers_source = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()

    assert "from container_commander.engine import list_containers" not in runtime_source
    assert "from container_commander.engine import list_containers" not in containers_source
    assert "from container_commander.engine import start_stopped_container" not in containers_source
    assert "from container_commander.engine import stop_container" not in containers_source


def test_host_companion_and_uninstall_endpoints_use_mcp_inspect(monkeypatch):
    containers = _load_module("commander_api.containers")

    monkeypatch.setattr(
        containers,
        "inspect_container_via_mcp",
        lambda container_id: {"blueprint_id": "bp-demo", "running": False},
    )

    monkeypatch.setattr(
        containers,
        "remove_stopped_container",
        lambda container_id: {"removed": True},
        raising=False,
    )
    monkeypatch.setattr(containers, "check_host_companion_via_mcp", lambda blueprint_id: {"checked": True, "blueprint_id": blueprint_id}, raising=False)
    monkeypatch.setattr(containers, "repair_host_companion_via_mcp", lambda blueprint_id: {"repaired": False, "skipped": True, "reason": "host_companion_runtime_not_implemented_in_v2"}, raising=False)
    monkeypatch.setattr(containers, "uninstall_host_companion_via_mcp", lambda blueprint_id: {"uninstalled": False, "skipped": True, "reason": "host_companion_runtime_not_implemented_in_v2", "removed_paths": []}, raising=False)
    monkeypatch.setattr(containers, "get_package_manifest_via_mcp", lambda blueprint_id: {"host_companion": {"enabled": True}}, raising=False)

    checked = asyncio.run(containers.api_check_host_companion("c1"))
    repaired = asyncio.run(containers.api_repair_host_companion("c1"))
    uninstalled = asyncio.run(containers.api_uninstall_host_companion("c1"))
    removed = asyncio.run(containers.api_uninstall_container("c1"))

    assert checked["checked"] is True
    assert checked["blueprint_id"] == "bp-demo"
    assert repaired["repaired"] is False
    assert repaired["result"]["reason"] == "host_companion_runtime_not_implemented_in_v2"
    assert uninstalled["uninstalled"] is False
    assert uninstalled["result"]["reason"] == "host_companion_runtime_not_implemented_in_v2"
    assert removed["uninstalled"] is True


def test_host_companion_slice_no_longer_uses_direct_legacy_imports():
    containers_source = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()
    assert "from container_commander.host_companions import check_host_companion" not in containers_source
    assert "from container_commander.host_companions import repair_host_companion" not in containers_source
    assert "from container_commander.host_companions import uninstall_host_companion" not in containers_source
    assert "from container_commander.host_companions import get_package_manifest" not in containers_source


def test_inspect_slice_no_longer_uses_direct_legacy_imports():
    containers_source = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()
    assert "from container_commander.engine import inspect_container" not in containers_source
