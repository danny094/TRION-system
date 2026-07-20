import io
import tarfile
from pathlib import Path
import sqlite3
import sys


SERVER_DIR = Path(__file__).resolve().parents[1] / "mcp-servers" / "container-commander"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from blueprint_store import get_blueprint, list_blueprints  # noqa: E402
from blueprint_write import create_blueprint, delete_blueprint, export_blueprint_yaml, import_blueprint_yaml, update_blueprint  # noqa: E402
from dashboard_views import get_dashboard_overview  # noqa: E402
from exec_views import exec_in_container, exec_in_container_detailed  # noqa: E402
from network_views import cleanup_networks, get_network_info, list_networks  # noqa: E402
from proxy_views import ensure_proxy_running, get_whitelist, set_whitelist, stop_proxy  # noqa: E402
from runtime_views import _managed_flags, cleanup_all as runtime_cleanup_all, get_container_stats, get_runtime_quota, inspect_container, remove_stopped_container as runtime_remove_stopped_container, start_stopped_container, stop_container  # noqa: E402
from volume_views import cleanup_orphaned_volumes, create_snapshot, delete_snapshot, get_volume, list_snapshots, list_volumes, remove_volume, restore_snapshot  # noqa: E402


def _init_blueprint_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE blueprints (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                dockerfile TEXT DEFAULT '',
                image TEXT DEFAULT '',
                runtime TEXT DEFAULT '',
                ports_json TEXT DEFAULT '[]',
                mounts_json TEXT DEFAULT '[]',
                environment_json TEXT DEFAULT '{}',
                resources_json TEXT DEFAULT '{}',
                tags_json TEXT DEFAULT '[]',
                icon TEXT DEFAULT '📦',
                created_at TEXT,
                updated_at TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO blueprints (
                id, name, description, dockerfile, image, runtime, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("demo", "Demo", "Example blueprint", "FROM python:3.12", "python:3.12", "docker", "2026-05-15T10:00:00Z", "2026-05-15T11:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()


def test_managed_flags_are_conservative():
    managed, actions_allowed, protected = _managed_flags({"trion.managed": "true"})
    assert managed is True
    assert actions_allowed is True
    assert protected is False

    managed, actions_allowed, protected = _managed_flags({"trion.managed": "true", "trion.protected": "true"})
    assert managed is True
    assert actions_allowed is False
    assert protected is True


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


def test_blueprint_views_use_v2_shape(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    _init_blueprint_db(db_path)
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    import blueprint_store  # noqa: E402

    blueprint_store.DB_PATH = str(db_path)

    listed = list_blueprints()
    assert listed == {
        "blueprints": [
            {
                "blueprint_id": "demo",
                "name": "Demo",
                "description": "Example blueprint",
                "version": "2026-05-15T11:00:00Z",
            }
        ]
    }

    detail = get_blueprint("demo")
    assert detail["blueprint"]["blueprint_id"] == "demo"
    assert detail["blueprint"]["definition"]["dockerfile"] == "FROM python:3.12"
    assert detail["blueprint"]["definition"]["image"] == "python:3.12"


def test_blueprint_write_roundtrip_uses_v2_store(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    import blueprint_store  # noqa: E402
    import blueprint_store_db  # noqa: E402
    import blueprint_write  # noqa: E402

    blueprint_store.DB_PATH = str(db_path)
    blueprint_store_db.DB_PATH = str(db_path)
    blueprint_write.get_conn.__globals__["DB_PATH"] = str(db_path)

    created = create_blueprint(
        {
            "id": "writer",
            "name": "Writer",
            "description": "Write path",
            "dockerfile": "FROM python:3.12",
            "tags": ["gpu"],
        }
    )
    assert created["created"] is True
    assert created["blueprint"]["blueprint_id"] == "writer"

    updated = update_blueprint("writer", {"description": "Updated", "tags": ["cpu"]})
    assert updated["updated"] is True
    assert updated["blueprint"]["definition"]["description"] == "Updated"
    assert updated["blueprint"]["definition"]["tags"] == ["cpu"]

    exported = export_blueprint_yaml("writer")
    assert "yaml" in exported
    assert "Writer" in exported["yaml"]

    imported = import_blueprint_yaml(
        """
id: imported
name: Imported
description: Imported blueprint
dockerfile: FROM alpine:3.20
"""
    )
    assert imported["created"] is True
    assert imported["blueprint"]["blueprint_id"] == "imported"

    deleted = delete_blueprint("writer")
    assert deleted == {"deleted": True, "blueprint_id": "writer"}


class _FakeContainer:
    def __init__(self, *, status="exited", managed=True, protected=False, cid="c1", name="demo", labels=None, manifest=None):
        self.id = cid
        self.name = name
        self.status = status
        self.labels = dict(labels or {})
        if managed and "trion.managed" not in self.labels:
            self.labels["trion.managed"] = "true"
        if protected and "trion.protected" not in self.labels:
            self.labels["trion.protected"] = "true"
        self.attrs = {
            "Config": {"Image": "demo:latest"},
            "Created": "2026-05-15T10:00:00Z",
            "State": {"Status": status, "Running": status == "running"},
            "NetworkSettings": {
                "Networks": {"bridge": {"IPAddress": "172.18.0.12"}},
                "Ports": {"8080/tcp": [{"HostPort": "18080", "HostIp": "127.0.0.1"}]},
            },
        }
        self.started = False
        self.stopped = False
        self._manifest = manifest

    def reload(self):
        self.attrs["State"]["Status"] = self.status
        self.attrs["State"]["Running"] = self.status == "running"

    def start(self):
        self.started = True
        self.status = "running"

    def stop(self, timeout=10):
        self.stopped = True
        self.status = "exited"

    def remove(self, force=True):
        self.removed = True

    def exec_run(self, args, demux=False, workdir=None):
        class _Result:
            def __init__(self, exit_code, output):
                self.exit_code = exit_code
                self.output = output

        if demux:
            if "pwd" in str(args or ""):
                return _Result(0, (b"/workspace\n", b""))
            return _Result(0, (b"ok\n", b""))
        if self._manifest is None:
            return _Result(1, b"")
        return _Result(0, self._manifest.encode("utf-8"))

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
    def __init__(self, container, networks=None):
        self.containers = self
        self._container = container
        self.networks = _FakeNetworks(networks or [])

    def get(self, container_id):
        return self._container


class _FakeNetwork:
    def __init__(self, name="trion-sandbox", short_id="net1", labels=None, internal=True, driver="bridge", containers=None):
        self.name = name
        self.short_id = short_id
        self.removed = False
        self.attrs = {
            "Labels": dict(labels or {"trion.managed": "true", "trion.network.type": "internal"}),
            "Internal": internal,
            "Driver": driver,
            "Containers": dict(containers or {}),
        }

    def remove(self):
        self.removed = True


class _FakeNetworks:
    def __init__(self, networks):
        self._networks = {network.name: network for network in networks}

    def list(self, filters=None):
        return list(self._networks.values())

    def get(self, name):
        if name not in self._networks:
            raise type("NotFound", (Exception,), {})()
        return self._networks[name]


class _FakeVolume:
    def __init__(self, name="trion_ws_demo_1", labels=None, created_at="2026-05-15T10:00:00Z", driver="local", mountpoint="/var/lib/docker/volumes/demo"):
        self.name = name
        self.attrs = {
            "Labels": dict(labels or {"trion.managed": "true", "trion.blueprint": "demo", "trion.created": created_at}),
            "CreatedAt": created_at,
            "Driver": driver,
            "Mountpoint": mountpoint,
        }
        self.removed = False

    def remove(self, force=False):
        self.removed = True


class _FakeVolumes:
    def __init__(self, volumes):
        self._volumes = {volume.name: volume for volume in volumes}

    def list(self, filters=None):
        return list(self._volumes.values())

    def get(self, volume_name):
        if volume_name not in self._volumes:
            raise type("NotFound", (Exception,), {})()
        return self._volumes[volume_name]


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


def test_volume_views_expose_v2_shapes(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    snapshot_file = snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz"
    snapshot_file.write_bytes(b"snapshot")
    volume = _FakeVolume()
    monkeypatch.setattr("volume_views._client", lambda: type("_Client", (), {"volumes": _FakeVolumes([volume])})())
    monkeypatch.setattr("volume_views.SNAPSHOT_DIR", str(snapshot_dir))

    listed = list_volumes()
    assert listed["volumes"][0]["name"] == "trion_ws_demo_1"

    snapshots = list_snapshots("trion_ws_demo_1")
    assert snapshots["snapshots"][0]["filename"].startswith("trion_ws_demo_1")

    detail = get_volume("trion_ws_demo_1")
    assert detail["volume"]["snapshots"][0]["filename"].endswith(".tar.gz")


def test_remove_volume_returns_removed_flag(monkeypatch):
    volume = _FakeVolume()
    monkeypatch.setattr("volume_views._client", lambda: type("_Client", (), {"volumes": _FakeVolumes([volume])})())

    removed = remove_volume("trion_ws_demo_1")
    assert removed == {"removed": True, "volume": "trion_ws_demo_1"}
    assert volume.removed is True


def test_cleanup_orphaned_volumes_respects_dry_run(monkeypatch):
    attached = _FakeVolume(name="trion_ws_attached")
    orphan = _FakeVolume(name="trion_ws_orphan")
    container = _FakeContainer(status="running", cid="c1", name="demo")
    container.attrs["Mounts"] = [{"Name": "trion_ws_attached"}]

    monkeypatch.setattr(
        "volume_views._client",
        lambda: type("_Client", (), {"volumes": _FakeVolumes([attached, orphan]), "containers": type("_Containers", (), {"list": lambda self, all=True: [container]})()})(),
    )

    dry_run = cleanup_orphaned_volumes(dry_run=True)
    assert dry_run == {"orphaned": ["trion_ws_orphan"], "dry_run": True}
    assert orphan.removed is False

    removed = cleanup_orphaned_volumes(dry_run=False)
    assert removed == {"orphaned": ["trion_ws_orphan"], "dry_run": False}
    assert orphan.removed is True


def test_delete_snapshot_returns_deleted_flag(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    snapshot_file = snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz"
    snapshot_file.write_bytes(b"snapshot")
    monkeypatch.setattr("volume_views.SNAPSHOT_DIR", str(snapshot_dir))

    deleted = delete_snapshot(snapshot_file.name)
    assert deleted == {"deleted": True, "filename": snapshot_file.name}
    assert not snapshot_file.exists()

    missing = delete_snapshot("missing.tar.gz")
    assert missing == {"deleted": False, "filename": "missing.tar.gz"}


def test_create_snapshot_returns_created_flag(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    monkeypatch.setattr("volume_views.SNAPSHOT_DIR", str(snapshot_dir))

    archive_payload = b"snapshot-bytes"
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as outer_tar:
        info = tarfile.TarInfo(name="snapshot.tar.gz")
        info.size = len(archive_payload)
        outer_tar.addfile(info, io.BytesIO(archive_payload))
    tar_bytes = tar_stream.getvalue()

    class _FakeSnapshotContainer:
        def __init__(self):
            self.removed = False

        def wait(self, timeout=120):
            return {"StatusCode": 0}

        def get_archive(self, path):
            return [tar_bytes], {"size": len(tar_bytes)}

        def remove(self, force=True):
            self.removed = True

    class _FakeVolumes:
        def get(self, volume_name):
            return type("_Volume", (), {"name": volume_name})()

    class _FakeContainers:
        def run(self, *args, **kwargs):
            return _FakeSnapshotContainer()

    class _FakeClient:
        def __init__(self):
            self.volumes = _FakeVolumes()
            self.containers = _FakeContainers()

    monkeypatch.setattr("volume_views._client", lambda: _FakeClient())

    created = create_snapshot("trion_ws_demo_1", tag="nightly")
    assert created["created"] is True
    assert created["filename"].startswith("trion_ws_demo_1_nightly_")
    assert (snapshot_dir / created["filename"]).read_bytes() == archive_payload


def test_restore_snapshot_returns_restored_flag(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    snapshot_file = snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz"
    snapshot_file.write_bytes(b"snapshot-bytes")
    monkeypatch.setattr("volume_views.SNAPSHOT_DIR", str(snapshot_dir))

    class _FakeRestoreContainer:
        def __init__(self):
            self.put_calls = []
            self.started = False
            self.removed = False

        def put_archive(self, path, data):
            self.put_calls.append((path, data))
            return True

        def start(self):
            self.started = True

        def wait(self, timeout=120):
            return {"StatusCode": 0}

        def remove(self, force=True):
            self.removed = True

    class _FakeVolumes:
        def __init__(self):
            self.created = []

        def get(self, volume_name):
            raise type("NotFound", (Exception,), {})()

        def create(self, **kwargs):
            self.created.append(kwargs)
            return type("_Volume", (), {"name": kwargs.get("name", "")})()

    class _FakeContainers:
        def __init__(self):
            self.container = _FakeRestoreContainer()

        def create(self, *args, **kwargs):
            return self.container

    class _FakeClient:
        def __init__(self):
            self.volumes = _FakeVolumes()
            self.containers = _FakeContainers()

    monkeypatch.setattr("volume_views._client", lambda: _FakeClient())

    restored = restore_snapshot(snapshot_file.name, target_volume="trion_ws_restored")
    assert restored == {
        "restored": True,
        "volume": "trion_ws_restored",
        "filename": snapshot_file.name,
    }
