from container_commander_v2_fakes import _FakeClient, _FakeContainer

from exec_views import exec_in_container, exec_in_container_detailed  # noqa: E402
from runtime_actions_views import cleanup_all as runtime_cleanup_all, remove_stopped_container as runtime_remove_stopped_container, start_stopped_container, stop_container  # noqa: E402
from runtime_views import _managed_flags, get_container_stats, get_runtime_quota, inspect_container, list_containers  # noqa: E402


def test_managed_flags_are_conservative():
    managed, actions_allowed, protected = _managed_flags({"trion.managed": "true"})
    assert managed is True
    assert actions_allowed is True
    assert protected is False

    managed, actions_allowed, protected = _managed_flags({"trion.managed": "true", "trion.protected": "true"})
    assert managed is True
    assert actions_allowed is False
    assert protected is True


def test_container_list_uses_inspect_image_when_image_object_is_stale(monkeypatch):
    container = _FakeContainer(status="running")

    class _StaleImageContainer(type(container)):
        @property
        def image(self):
            raise RuntimeError("No such image")

    container.__class__ = _StaleImageContainer
    monkeypatch.setattr("runtime_views._client", lambda: type("Client", (), {"containers": type("Containers", (), {"list": lambda self, all=True: [container]})()})())

    assert list_containers()["containers"][0]["image"] == "demo:latest"


def test_container_stats_returns_v2_shape(monkeypatch):
    container = _FakeContainer(status="running")
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(container))

    result = get_container_stats("c1")

    assert result["container_id"] == "c1"
    assert result["cpu_percent"] == 40.0
    assert result["memory_mb"] == 256.0
    assert result["memory_limit_mb"] == 1024.0
    assert result["network_rx_bytes"] == 1234
    assert result["network_tx_bytes"] == 5678
    assert result["ip_address"] == "172.18.0.12"
    assert result["ports"][0]["host"] == "18080"
    assert result["efficiency"]["level"] in {"green", "yellow", "red"}


def test_runtime_quota_returns_v2_shape(monkeypatch):
    managed = _FakeContainer(status="running", labels={"trion.managed": "true", "trion.blueprint": "demo"}, cid="c-managed")
    managed.attrs["HostConfig"] = {"Memory": 512 * 1024 * 1024, "NanoCpus": 1_500_000_000}
    unmanaged = _FakeContainer(status="running", managed=False, cid="c-unmanaged")
    unmanaged.attrs["HostConfig"] = {"Memory": 1024 * 1024 * 1024, "NanoCpus": 2_000_000_000}

    class _FakeContainers:
        def list(self, all=True):
            return [managed, unmanaged]

    class _FakeClientAll:
        def __init__(self):
            self.containers = _FakeContainers()

    monkeypatch.setenv("COMMANDER_MAX_MEMORY_MB", "4096")
    monkeypatch.setenv("COMMANDER_MAX_CPU", "6")
    monkeypatch.setenv("COMMANDER_MAX_CONTAINERS", "7")
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClientAll())

    result = get_runtime_quota()

    assert result == {
        "max_containers": 7,
        "max_total_memory_mb": 4096,
        "max_total_cpu": 6.0,
        "containers_used": 1,
        "memory_used_mb": 512,
        "cpu_used": 1.5,
    }


def test_container_exec_views_return_v2_shapes(monkeypatch):
    container = _FakeContainer(status="running", labels={"trion.managed": "true", "trion.blueprint": "demo"})
    monkeypatch.setattr("exec_views._client", lambda: _FakeClient(container))
    monkeypatch.setattr("exec_views.get_blueprint", lambda blueprint_id: {"blueprint": {"definition": {"allowed_exec": ["pwd"]}}})

    simple = exec_in_container("c1", "pwd", timeout=5)
    detailed = exec_in_container_detailed("c1", "pwd", timeout=5)

    assert simple["exit_code"] == 0
    assert "/workspace" in simple["output"]
    assert detailed["exit_code"] == 0
    assert detailed["stdout"] == "/workspace"
    assert detailed["stderr"] == ""
    assert detailed["container_id"] == "c1"


def test_runtime_cleanup_all_removes_only_managed_containers(monkeypatch):
    managed = _FakeContainer(status="running", labels={"trion.managed": "true", "trion.blueprint": "demo"}, cid="c-managed")
    unmanaged = _FakeContainer(status="running", managed=False, cid="c-unmanaged")

    class _FakeContainers:
        def list(self, all=True):
            return [managed, unmanaged]

    class _FakeClientAll:
        def __init__(self):
            self.containers = _FakeContainers()

    monkeypatch.setattr("runtime_views._client", lambda: _FakeClientAll())

    result = runtime_cleanup_all()

    assert result["cleaned"] is True
    assert result["removed"] == ["c-managed"]
    assert result["errors"] == []
    assert managed.stopped is True
    assert unmanaged.stopped is False


def test_remove_stopped_container_only_removes_managed_stopped_container(monkeypatch):
    managed = _FakeContainer(status="exited", labels={"trion.managed": "true", "trion.blueprint": "demo"}, cid="c-managed")
    running = _FakeContainer(status="running", labels={"trion.managed": "true", "trion.blueprint": "demo"}, cid="c-running")
    unmanaged = _FakeContainer(status="exited", managed=False, cid="c-unmanaged")

    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(managed))
    removed = runtime_remove_stopped_container("c-managed")
    assert removed == {"removed": True, "container_id": "c-managed", "blueprint_id": "demo"}
    assert managed.removed is True

    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(running))
    blocked = runtime_remove_stopped_container("c-running")
    assert blocked == {"removed": False, "container_id": "c-running", "reason": "running"}

    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(unmanaged))
    denied = runtime_remove_stopped_container("c-unmanaged")
    assert denied == {"removed": False, "container_id": "c-unmanaged", "reason": "not_managed"}


def test_start_stop_actions_are_guarded_and_idempotent(monkeypatch):
    unmanaged = _FakeContainer(managed=False)
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(unmanaged))
    denied = start_stopped_container("c1")
    assert denied["ok"] is False
    assert denied["error"]["code"] == "ACTION_NOT_ALLOWED"

    running = _FakeContainer(status="running")
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(running))
    already = start_stopped_container("c1")
    assert already["ok"] is True
    assert already["action"] == "already_running"

    stopped = _FakeContainer(status="exited")
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(stopped))
    started = start_stopped_container("c1")
    assert started["ok"] is True
    assert started["action"] == "started"
    assert stopped.started is True

    stopped_again = stop_container("c1")
    assert stopped_again["ok"] is True
    assert stopped_again["action"] == "stopped"


def test_inspect_container_exposes_home_scope(monkeypatch):
    manifest = (
        '{"home_id":"trion-home","blueprint_id":"trion-home","owner_agent":"trion",'
        '"runtime_profile":"trion-home","roots":{"home":"/home/trion"},'
        '"rules":{"allowed_write_roots":["/home/trion/notes","/home/trion/workspace"]}}'
    )
    container = _FakeContainer(
        status="running",
        name="trion-home",
        labels={
            "trion.managed": "true",
            "trion.home": "true",
            "trion.role": "home",
            "trion.profile": "trion-home",
            "trion.blueprint": "trion-home",
        },
        manifest=manifest,
    )
    monkeypatch.setattr("runtime_views._client", lambda: _FakeClient(container))
    result = inspect_container("c1")
    details = result["container"]
    assert details["blueprint_id"] == "trion-home"
    assert details["home_scope"]["is_home"] is True
    assert details["home_scope"]["manifest_readable"] is True
    assert details["home_scope"]["home_root"] == "/home/trion"
    assert details["home_scope"]["owner_agent"] == "trion"
