import asyncio
import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_lifecycle_slice_no_longer_imports_vendor_engine_entrypoints():
    routes_source = (ADMIN_API_DIR / "commander_routes.py").read_text()
    approval_source = (ADMIN_API_DIR / "commander_approval_workflow.py").read_text()
    containers_source = (ADMIN_API_DIR / "commander_api" / "containers.py").read_text()

    assert "from container_commander.engine import start_container" not in routes_source
    assert "from container_commander.engine import start_container" not in approval_source
    assert "from container_commander.engine import remove_stopped_container" not in containers_source
    lifecycle_source = (ADMIN_API_DIR / "commander_container_lifecycle.py").read_text()
    assert "from container_commander.engine import remove_stopped_container" not in lifecycle_source


def test_deploy_orchestrator_uses_local_blueprint_env_and_audit_truths():
    source = (ADMIN_API_DIR / "commander_deploy_orchestrator.py").read_text()
    runtime_client_source = (ADMIN_API_DIR / "commander_deploy_runtime_client.py").read_text()

    assert "from commander_deploy_blueprints import resolve_blueprint" in source
    assert "from commander_audit_store import log_action" in source
    assert "from commander_deploy_blueprint_runtime import (" in source
    assert "from commander_deploy_container_run import start_runtime_container" in source
    assert "from commander_deploy_image import build_image" in source
    assert "from commander_deploy_postchecks import run_post_start_checks" in source
    assert "from commander_deploy_runtime_client import emit_ws_activity, get_runtime_client, validate_runtime_preflight" in source
    assert "from commander_deploy_runtime_state import (" in source
    assert "from commander_deploy_start_env import build_env_vars, prepare_runtime_blueprint, setup_host_companion" in source
    assert "from commander_deploy_support import (" in source
    assert "from commander_deploy_trust import enforce_trust_gates, request_deploy_approval_if_needed" in source
    assert "from store.inheritance import resolve_blueprint" not in source
    assert "from store.log import log_action" not in source
    assert "from engine.container_run import start_runtime_container" not in source
    assert "from engine.blueprint_runtime import (" not in source
    assert "from engine.image import build_image" not in source
    assert "from engine.quota import commit_quota_reservation, release_quota_reservation, reserve_quota" not in source
    assert "from engine.state import apply_refs, build_refs, set_ttl_timer, sync_from_docker" not in source
    assert "from engine.start_checks import run_post_start_checks" not in source
    assert "from engine.client import emit_ws_activity" not in source
    assert "from engine.start_env import build_env_vars, prepare_runtime_blueprint, setup_host_companion" not in source
    assert "from engine.deploy_support import (" not in source
    assert "from engine.start_trust import enforce_trust_gates, request_deploy_approval_if_needed" not in source
    assert '__import__("engine.client"' not in source
    assert "from package_runtime_views import apply_package_runtime_views" not in source
    assert "from secret_store import get_secret_value, get_secrets_for_blueprint, log_secret_access" not in source
    assert "from engine.client import get_client" not in runtime_client_source


def test_deploy_route_uses_local_lifecycle_facade(monkeypatch):
    routes = _load_module("commander_routes")

    class _FakeInstance:
        container_id = "c-demo"
        block_apply_handoff_resource_ids_requested = ["gpu0"]
        block_apply_handoff_resource_ids_applied = ["gpu0"]
        hardware_resolution_preview = {"ok": True}

        def model_dump(self):
            return {"container_id": self.container_id}

    calls = {}

    def _fake_start_container(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return _FakeInstance()

    monkeypatch.setattr(routes, "start_container", _fake_start_container, raising=False)

    result = asyncio.run(
        routes.api_deploy_container(
            _FakeRequest(
                {
                    "blueprint_id": "demo",
                    "conversation_id": "conv-1",
                    "session_id": "sess-1",
                    "environment": {"A": "1"},
                    "block_apply_handoff_resource_ids": ["gpu0"],
                }
            )
        )
    )

    assert result["deployed"] is True
    assert result["container"]["container_id"] == "c-demo"
    assert calls["args"][0] == "demo"
    assert calls["args"][2] == {"A": "1"}
    assert calls["kwargs"]["block_apply_handoff_resource_ids"] == ["gpu0"]
    assert calls["kwargs"]["conversation_id"] == "conv-1"
    assert calls["kwargs"]["session_id"] == "sess-1"


def test_approval_workflow_uses_local_lifecycle_facade(monkeypatch):
    workflow = _load_module("commander_approval_workflow")
    contracts = _load_module("commander_approval_contracts")
    runtime_models = _load_module("commander_runtime_models")

    approval = contracts.PendingApproval(
        blueprint_id="bp-demo",
        reason="Need approval",
        network_mode=runtime_models.NetworkMode.NONE,
        session_id="sess-1",
        conversation_id="conv-1",
    )

    monkeypatch.setitem(workflow._pending, approval.id, approval)
    monkeypatch.setitem(workflow._callbacks, approval.id, workflow.threading.Event())
    monkeypatch.setattr(workflow, "save_unlocked", lambda: None, raising=False)
    monkeypatch.setattr(workflow, "_emit_ws_activity", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(workflow, "log_action", lambda *args, **kwargs: None, raising=False)

    calls = {}

    class _FakeInstance:
        container_id = "c-approved"

        def model_dump(self):
            return {"container_id": self.container_id}

    def _fake_start_container(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return _FakeInstance()

    monkeypatch.setattr(workflow, "start_container", _fake_start_container, raising=False)

    result = workflow.approve(approval.id, approved_by="user")

    assert result == {"container_id": "c-approved"}
    assert calls["kwargs"]["blueprint_id"] == "bp-demo"
    assert calls["kwargs"]["skip_approval"] is True
    assert calls["kwargs"]["conversation_id"] == "conv-1"
    assert calls["kwargs"]["session_id"] == "sess-1"


def test_uninstall_container_uses_local_lifecycle_facade(monkeypatch):
    containers = _load_module("commander_api.containers")

    monkeypatch.setattr(
        containers,
        "inspect_container_via_mcp",
        lambda container_id: {"blueprint_id": "bp-demo", "running": False},
    )
    monkeypatch.setattr(
        containers,
        "get_package_manifest_via_mcp",
        lambda blueprint_id: {"host_companion": {"enabled": True}},
        raising=False,
    )
    monkeypatch.setattr(
        containers,
        "uninstall_host_companion_via_mcp",
        lambda blueprint_id: {"uninstalled": False, "skipped": True, "reason": "host_companion_runtime_not_implemented_in_v2", "removed_paths": []},
        raising=False,
    )

    calls = {}

    def _fake_remove(container_id):
        calls["container_id"] = container_id
        return {"removed": True}

    monkeypatch.setattr(containers, "remove_stopped_container", _fake_remove, raising=False)

    result = asyncio.run(containers.api_uninstall_container("c1"))

    assert result["uninstalled"] is True
    assert calls["container_id"] == "c1"


def test_lifecycle_facade_uses_mcp_remove_contract(monkeypatch):
    lifecycle = _load_module("commander_container_lifecycle")

    calls = {}

    def _fake_remove(container_id, timeout=5.0):
        calls["container_id"] = container_id
        return {"removed": True, "container_id": container_id}

    monkeypatch.setattr(lifecycle, "remove_stopped_container_via_mcp", _fake_remove, raising=False)

    result = lifecycle.remove_stopped_container("c1")

    assert result == {"removed": True, "container_id": "c1"}
    assert calls["container_id"] == "c1"
