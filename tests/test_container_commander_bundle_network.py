import container_commander_bundle_fakes  # noqa: F401
import bundle_blueprint_store  # noqa: E402
import bundle_docker  # noqa: E402
import server as commander_bundle  # noqa: E402


def test_bundle_network_views_use_v2_shapes(monkeypatch):
    class _FakeContainer:
        def __init__(self):
            self.attrs = {
                "NetworkSettings": {
                    "Networks": {
                        "trion-sandbox": {
                            "IPAddress": "172.20.0.2",
                            "Gateway": "172.20.0.1",
                            "MacAddress": "02:42:ac:14:00:02",
                        }
                    }
                }
            }

    class _FakeNetwork:
        def __init__(self):
            self.name = "trion-sandbox"
            self.short_id = "net1"
            self.attrs = {
                "Labels": {"trion.managed": "true", "trion.network.type": "internal"},
                "Internal": True,
                "Driver": "bridge",
                "Containers": {"cid1": {"Name": "demo"}},
            }

    class _FakeClient:
        def __init__(self):
            self.containers = self
            self.networks = type("_Networks", (), {"list": lambda self, filters=None: [_FakeNetwork()]})()

        def get(self, container_id):
            return _FakeContainer()

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient())

    listed = commander_bundle.list_networks()
    assert listed["networks"][0]["name"] == "trion-sandbox"
    detail = commander_bundle.get_network_info("c1")
    assert detail["networks"]["trion-sandbox"]["ip"] == "172.20.0.2"


def test_bundle_container_exec_returns_v2_shapes(monkeypatch):
    class _FakeContainer:
        status = "running"
        id = "c1"
        labels = {"trion.managed": "true", "trion.blueprint": "demo"}

        def exec_run(self, args, demux=False, workdir=None):
            class _Result:
                def __init__(self, exit_code, output):
                    self.exit_code = exit_code
                    self.output = output

            if demux:
                return _Result(0, (b"/workspace\n", b""))
            return _Result(0, b"")

    class _FakeClient:
        def __init__(self):
            self.containers = self

        def get(self, container_id):
            return _FakeContainer()

        def list(self, all=True):
            return []

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient())
    monkeypatch.setattr(bundle_blueprint_store, "get_blueprint", lambda blueprint_id: {"blueprint": {"definition": {"allowed_exec": ["pwd"]}}})

    simple = commander_bundle.container_exec("c1", "pwd", timeout=5)
    detailed = commander_bundle.container_exec_detailed("c1", "pwd", timeout=5)

    assert simple["exit_code"] == 0
    assert "/workspace" in simple["output"]
    assert detailed["exit_code"] == 0
    assert detailed["stdout"] == "/workspace"
    assert detailed["stderr"] == ""


def test_bundle_network_cleanup_only_removes_empty_isolated_networks(monkeypatch):
    class _FakeNetwork:
        def __init__(self, name, network_type, containers):
            self.name = name
            self.short_id = name
            self.removed = False
            self.attrs = {
                "Labels": {"trion.managed": "true", "trion.network.type": network_type},
                "Internal": True,
                "Driver": "bridge",
                "Containers": containers,
            }

        def remove(self):
            self.removed = True

    class _FakeNetworks:
        def __init__(self, networks):
            self._networks = {network.name: network for network in networks}

        def list(self, filters=None):
            return list(self._networks.values())

        def get(self, name):
            return self._networks[name]

    class _FakeClient:
        def __init__(self, networks):
            self.networks = _FakeNetworks(networks)

    iso_empty = _FakeNetwork("trion-iso-empty", "isolated", {})
    iso_used = _FakeNetwork("trion-iso-used", "isolated", {"cid1": {"Name": "demo"}})
    shared = _FakeNetwork("trion-sandbox", "internal", {})
    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient([iso_empty, iso_used, shared]))

    result = commander_bundle.cleanup_networks()
    assert result == {"removed": ["trion-iso-empty"]}
    assert iso_empty.removed is True
    assert iso_used.removed is False
    assert shared.removed is False


def test_bundle_proxy_views_persist_enabled_state_and_whitelist(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    started = commander_bundle.ensure_proxy_running()
    updated = commander_bundle.set_whitelist("bp-demo", ["Example.com", "example.com", " api.openai.com "])
    listed = commander_bundle.get_whitelist("bp-demo")
    stopped = commander_bundle.stop_proxy()

    assert started == {"started": True, "enabled": True}
    assert updated == {
        "updated": True,
        "blueprint_id": "bp-demo",
        "domains": ["example.com", "api.openai.com"],
    }
    assert listed == {
        "blueprint_id": "bp-demo",
        "domains": ["example.com", "api.openai.com"],
        "enabled": True,
    }
    assert stopped == {"stopped": True, "enabled": False}
