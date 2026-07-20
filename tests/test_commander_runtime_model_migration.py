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


def test_runtime_model_slice_no_longer_imports_vendor_models_or_log():
    approval_contracts = (ADMIN_API_DIR / "commander_approval_contracts.py").read_text()
    approval_workflow = (ADMIN_API_DIR / "commander_approval_workflow.py").read_text()
    approval_policy = (ADMIN_API_DIR / "commander_approval_policy.py").read_text()
    commander_routes = (ADMIN_API_DIR / "commander_routes.py").read_text()

    assert "from container_commander.models import NetworkMode, ResourceLimits" not in approval_contracts
    assert "from container_commander.models import NetworkMode, ResourceLimits" not in approval_workflow
    assert "from container_commander.models import NetworkMode" not in approval_policy
    assert "from container_commander.models import ResourceLimits" not in commander_routes
    assert "from container_commander.store.log import log_action" not in approval_workflow
    assert "from container_commander.engine import PendingApprovalError" not in commander_routes


def test_deploy_route_extracts_pending_approval_without_vendor_error_import(monkeypatch):
    routes = _load_module("commander_routes")

    class _SyntheticPending(Exception):
        def __init__(self):
            self.approval_id = "abc123"
            self.reason = "Need approval"
            super().__init__("pending approval")

    monkeypatch.setattr(
        routes,
        "start_container",
        lambda *args, **kwargs: (_ for _ in ()).throw(_SyntheticPending()),
        raising=False,
    )

    result = asyncio.run(
        routes.api_deploy_container(
            _FakeRequest(
                {
                    "blueprint_id": "demo",
                    "conversation_id": "conv-1",
                    "session_id": "sess-1",
                    "block_apply_handoff_resource_ids": ["gpu0"],
                }
            )
        )
    )

    assert result.status_code == 202
    assert result.body
    body = result.body.decode("utf-8")
    assert '"pending_approval":true' in body
    assert '"approval_id":"abc123"' in body
    assert '"reason":"Need approval"' in body
    assert '"conversation_id":"conv-1"' in body
    assert '"session_id":"sess-1"' in body


def test_deploy_support_helpers_are_local():
    deploy_support = _load_module("commander_deploy_support")

    bindings = deploy_support.build_port_bindings(["8080:80/tcp", "8443"])
    assert bindings["80/tcp"] == "8080"
    assert bindings["8443/tcp"] == "8443"

    healthcheck = deploy_support.build_healthcheck_config(
        {"test": "curl -f http://localhost/health", "interval_seconds": 5, "retries": 2}
    )
    assert healthcheck["test"] == ["CMD-SHELL", "curl -f http://localhost/health"]
    assert healthcheck["retries"] == 2


def test_deploy_image_helpers_are_local(monkeypatch):
    deploy_image = _load_module("commander_deploy_image")

    class _Images:
        def __init__(self):
            self.pulled = None

        def get(self, image):
            raise deploy_image.ImageNotFound("missing")

        def pull(self, image):
            self.pulled = image

    class _Client:
        def __init__(self):
            self.images = _Images()

    class _Blueprint:
        id = "bp1"
        image = "ghcr.io/demo/app:latest"
        dockerfile = ""

    monkeypatch.setattr(deploy_image, "get_runtime_client", lambda: _Client())

    assert deploy_image.blueprint_image_tag(_Blueprint()) == "ghcr.io/demo/app:latest"
    assert deploy_image.build_image(_Blueprint()) == "ghcr.io/demo/app:latest"


def test_deploy_postchecks_helper_uses_local_entry():
    deploy_postchecks = _load_module("commander_deploy_postchecks")

    class _Container:
        id = "c1"
        short_id = "c1"
        attrs = {"State": {"Running": True, "Health": {"Status": "healthy", "Log": []}}}

        def logs(self, **kwargs):
            return b""

    warnings = deploy_postchecks.run_post_start_checks(
        blueprint_id="bp1",
        bp=type("BP", (), {"healthcheck": {}})(),
        package_manifest=None,
        runtime={
            "container": _Container(),
            "client": object(),
            "volume_name": "v1",
            "created_workspace_volume": False,
            "healthcheck": {},
        },
        derive_readiness_timeout_seconds=lambda cfg: 30,
        wait_for_container_health=lambda *args, **kwargs: (True, "", "healthy"),
        cleanup_failed_container_start=lambda **kwargs: None,
        emit_ws_activity=lambda *args, **kwargs: None,
        log_action=lambda *args, **kwargs: None,
        logger=object(),
    )

    assert warnings == []


def test_deploy_blueprint_runtime_helpers_are_local():
    deploy_runtime = _load_module("commander_deploy_blueprint_runtime")

    mounts = deploy_runtime.normalize_runtime_mount_overrides(
        [{"host": "/tmp/demo", "container": "/workspace/demo", "mode": "rw", "type": "bind"}]
    )
    assert mounts[0].host == "/tmp/demo"
    assert deploy_runtime.runtime_mount_payloads(mounts)[0]["container"] == "/workspace/demo"

    devices = deploy_runtime.normalize_runtime_device_overrides(["/dev/dri/renderD128"])
    assert devices == ["/dev/dri/renderD128"]


def test_deploy_container_run_helpers_are_local():
    deploy_run = _load_module("commander_deploy_container_run")

    assert deploy_run.parse_memory("512m") == 512 * 1024 * 1024
    assert deploy_run.resolve_network("none")["network"] == "none"
    assert deploy_run.resolve_network("bridge")["network"] == "bridge"


def test_deploy_runtime_state_helpers_are_local(monkeypatch):
    deploy_state = _load_module("commander_deploy_runtime_state")
    runtime_models = _load_module("commander_runtime_models")
    models = _load_module("models")

    quota = runtime_models.SessionQuota(max_total_memory_mb=4096, max_total_cpu=8.0, max_containers=4)
    state = deploy_state.RuntimeStateRefs(
        active={},
        ttl_timers={},
        quota=quota,
        state_lock=object(),
        pending_starts=0,
        pending_memory_mb=0.0,
        pending_cpu=0.0,
        last_runtime_sync_monotonic=0.0,
    )
    state.state_lock = __import__("threading").RLock()

    resources = models.ResourceLimits(memory_limit="512m", memory_swap="1g", cpu_limit="1.0", pids_limit=256, timeout_seconds=0)
    mem_mb, cpu = deploy_state.reserve_quota(resources, state)
    assert int(mem_mb) == 512
    assert cpu == 1.0
