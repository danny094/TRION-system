import container_commander_bundle_fakes  # noqa: F401
import bundle_docker  # noqa: E402
import server as commander_bundle  # noqa: E402


def test_bundle_container_list_gracefully_degrades_without_runtime(monkeypatch):
    def fail_client():
        raise RuntimeError("docker unavailable")

    monkeypatch.setattr(bundle_docker, "get_docker_client", fail_client)
    result = commander_bundle.list_containers()
    assert result["ok"] is False
    assert result["error"]["code"] == "RUNTIME_UNAVAILABLE"


def test_bundle_container_list_uses_inspect_image_when_image_object_is_stale(monkeypatch):
    class _StaleImageContainer:
        id = "c1"
        name = "demo"
        status = "running"
        labels = {"trion.managed": "true"}
        attrs = {"Config": {"Image": "demo:latest"}, "Created": "2026-05-15T10:00:00Z"}

        @property
        def image(self):
            raise RuntimeError("No such image")

    client = type("Client", (), {"containers": type("Containers", (), {"list": lambda self, all=True: [_StaleImageContainer()]})()})()
    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: client)

    assert commander_bundle.list_containers()["containers"][0]["image"] == "demo:latest"


def test_bundle_container_stats_returns_v2_shape(monkeypatch):
    class _FakeContainer:
        labels = {"trion.managed": "true", "trion.blueprint": "bp-demo"}
        attrs = {
            "NetworkSettings": {
                "Networks": {"bridge": {"IPAddress": "172.18.0.12"}},
                "Ports": {"8080/tcp": [{"HostPort": "18080", "HostIp": "127.0.0.1"}]},
            }
        }

        def stats(self, stream=False):
            return {
                "cpu_stats": {
                    "cpu_usage": {"total_usage": 2_000_000_000},
                    "system_cpu_usage": 20_000_000_000,
                    "online_cpus": 4,
                },
                "precpu_stats": {
                    "cpu_usage": {"total_usage": 1_000_000_000},
                    "system_cpu_usage": 10_000_000_000,
                },
                "memory_stats": {"usage": 256 * 1024 * 1024, "limit": 1024 * 1024 * 1024},
                "networks": {"bridge": {"rx_bytes": 1234, "tx_bytes": 5678}},
            }

    class _FakeClient:
        def __init__(self):
            self.containers = self

        def get(self, container_id):
            return _FakeContainer()

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient())

    result = commander_bundle.get_container_stats("c1")

    assert result["container_id"] == "c1"
    assert result["cpu_percent"] == 40.0
    assert result["memory_mb"] == 256.0
    assert result["memory_limit_mb"] == 1024.0
    assert result["network_rx_bytes"] == 1234
    assert result["network_tx_bytes"] == 5678
    assert result["ip_address"] == "172.18.0.12"
    assert result["ports"][0]["host"] == "18080"


def test_bundle_runtime_quota_returns_v2_shape(monkeypatch):
    class _FakeManagedContainer:
        labels = {"trion.managed": "true", "trion.blueprint": "bp-demo"}
        attrs = {"HostConfig": {"Memory": 512 * 1024 * 1024, "NanoCpus": 1_500_000_000}}

    class _FakeUnmanagedContainer:
        labels = {}
        attrs = {"HostConfig": {"Memory": 1024 * 1024 * 1024, "NanoCpus": 2_000_000_000}}

    class _FakeClient:
        def __init__(self):
            self.containers = self

        def list(self, all=True):
            return [_FakeManagedContainer(), _FakeUnmanagedContainer()]

    monkeypatch.setenv("COMMANDER_MAX_MEMORY_MB", "4096")
    monkeypatch.setenv("COMMANDER_MAX_CPU", "6")
    monkeypatch.setenv("COMMANDER_MAX_CONTAINERS", "7")
    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient())

    result = commander_bundle.runtime_quota()

    assert result == {
        "max_containers": 7,
        "max_total_memory_mb": 4096,
        "max_total_cpu": 6.0,
        "containers_used": 1,
        "memory_used_mb": 512,
        "cpu_used": 1.5,
    }


def test_bundle_runtime_cleanup_all_removes_only_managed_containers(monkeypatch):
    class _FakeContainer:
        def __init__(self, container_id, managed=True):
            self.id = container_id
            self.status = "running"
            self.name = container_id
            self.labels = {"trion.managed": "true"} if managed else {}
            self.attrs = {"Config": {"Image": "demo:latest"}}
            self.stopped = False
            self.removed = False

        def stop(self, timeout=5):
            self.stopped = True

        def remove(self, force=True):
            self.removed = True

    managed = _FakeContainer("c-managed", managed=True)
    unmanaged = _FakeContainer("c-unmanaged", managed=False)

    class _FakeClient:
        def __init__(self):
            self.containers = self

        def list(self, all=True):
            return [managed, unmanaged]

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient())

    result = commander_bundle.runtime_cleanup_all()

    assert result["cleaned"] is True
    assert result["removed"] == ["c-managed"]
    assert result["errors"] == []
    assert managed.stopped is True
    assert managed.removed is True
    assert unmanaged.removed is False


def test_bundle_remove_stopped_container_behaves_like_v2_contract(monkeypatch):
    class _FakeContainer:
        def __init__(self, container_id, managed=True, running=False):
            self.id = container_id
            self.status = "running" if running else "exited"
            self.name = container_id
            self.labels = {"trion.managed": "true", "trion.blueprint": "demo"} if managed else {}
            self.attrs = {"Config": {"Image": "demo:latest"}, "State": {"Running": running}}
            self.removed = False

        def reload(self):
            return None

        def remove(self, force=True):
            self.removed = True

    managed = _FakeContainer("c-managed", managed=True, running=False)
    running = _FakeContainer("c-running", managed=True, running=True)
    unmanaged = _FakeContainer("c-unmanaged", managed=False, running=False)

    class _FakeClient:
        def __init__(self, container):
            self.containers = self
            self._container = container

        def get(self, container_id):
            return self._container

        def list(self, all=True):
            return []

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient(managed))
    removed = commander_bundle.remove_stopped_container("c-managed")
    assert removed == {"removed": True, "container_id": "c-managed", "blueprint_id": "demo"}
    assert managed.removed is True

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient(running))
    blocked = commander_bundle.remove_stopped_container("c-running")
    assert blocked == {"removed": False, "container_id": "c-running", "reason": "running"}

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient(unmanaged))
    denied = commander_bundle.remove_stopped_container("c-unmanaged")
    assert denied == {"removed": False, "container_id": "c-unmanaged", "reason": "not_managed"}
