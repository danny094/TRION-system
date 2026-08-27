from container_commander_v2_fakes import _FakeClient, _FakeContainer, _FakeNetwork

from dashboard_views import get_dashboard_overview  # noqa: E402
from network_views import cleanup_networks, get_network_info, list_networks  # noqa: E402
from proxy_views import ensure_proxy_running, get_whitelist, set_whitelist, stop_proxy  # noqa: E402


def test_network_views_expose_v2_shapes(monkeypatch):
    container = _FakeContainer(status="running", cid="c1", name="demo")
    container.attrs["NetworkSettings"] = {
        "Networks": {
            "trion-sandbox": {"IPAddress": "172.20.0.2", "Gateway": "172.20.0.1", "MacAddress": "02:42:ac:14:00:02"}
        }
    }
    fake_network = _FakeNetwork(containers={"cid1": {"Name": "demo"}})
    monkeypatch.setattr("network_views._client", lambda: _FakeClient(container, networks=[fake_network]))

    listed = list_networks()
    assert listed == {
        "networks": [
            {
                "name": "trion-sandbox",
                "id": "net1",
                "type": "internal",
                "internal": True,
                "driver": "bridge",
                "container_count": 1,
                "containers": ["demo"],
            }
        ]
    }

    detail = get_network_info("c1")
    assert detail["container_id"] == "c1"
    assert detail["networks"]["trion-sandbox"]["gateway"] == "172.20.0.1"


def test_network_cleanup_only_removes_empty_isolated_networks(monkeypatch):
    container = _FakeContainer(status="running", cid="c1", name="demo")
    iso_empty = _FakeNetwork(name="trion-iso-empty", labels={"trion.managed": "true", "trion.network.type": "isolated"}, containers={})
    iso_used = _FakeNetwork(name="trion-iso-used", labels={"trion.managed": "true", "trion.network.type": "isolated"}, containers={"cid1": {"Name": "demo"}})
    shared = _FakeNetwork(name="trion-sandbox", labels={"trion.managed": "true", "trion.network.type": "internal"}, containers={})
    monkeypatch.setattr("network_views._client", lambda: _FakeClient(container, networks=[iso_empty, iso_used, shared]))

    result = cleanup_networks()
    assert result == {"removed": ["trion-iso-empty"]}
    assert iso_empty.removed is True
    assert iso_used.removed is False
    assert shared.removed is False


def test_proxy_views_persist_enabled_state_and_whitelist(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    started = ensure_proxy_running()
    updated = set_whitelist("bp-demo", ["Example.com", "example.com", " api.openai.com "])
    listed = get_whitelist("bp-demo")
    stopped = stop_proxy()

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


def test_dashboard_view_aggregates_current_mcp_slices(monkeypatch):
    monkeypatch.setattr("dashboard_views.list_containers", lambda: {"containers": [{"status": "running"}, {"status": "exited"}]})
    monkeypatch.setattr("dashboard_views.list_blueprints", lambda: {"blueprints": [{"blueprint_id": "demo"}]})
    monkeypatch.setattr("dashboard_views.list_networks", lambda: {"networks": [{"name": "trion-sandbox"}]})
    monkeypatch.setattr("dashboard_views.list_volumes", lambda: {"volumes": [{"name": "trion_ws_demo"}]})
    monkeypatch.setattr("dashboard_views.get_whitelist", lambda blueprint_id: {"enabled": True, "domains": []})

    result = get_dashboard_overview()

    assert result["health"] == {
        "runtime": "ok",
        "blueprint_store": "ok",
        "proxy_policy": "enabled",
    }
    assert result["resources"]["containers"] == {"total": 2, "running": 1, "stopped": 1}
    assert result["resources"]["blueprints"]["total"] == 1
    assert result["resources"]["networks"]["total"] == 1
    assert result["resources"]["volumes"]["total"] == 1
    assert result["alerts"] == []
    assert result["events"] == []
