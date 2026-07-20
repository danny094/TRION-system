import io
import tarfile
from pathlib import Path
import json
import sqlite3
import sys


BUNDLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "container_commander_bundle"
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))

import server as commander_bundle  # noqa: E402


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
            (
                "demo",
                "Demo",
                "Example blueprint",
                "FROM python:3.12",
                "python:3.12",
                "docker",
                "2026-05-15T10:00:00Z",
                "2026-05-15T11:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_bundle_blueprint_views_use_v2_shape(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    _init_blueprint_db(db_path)
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))
    commander_bundle.DB_PATH = str(db_path)

    listed = commander_bundle.list_blueprints()
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

    detail = commander_bundle.get_blueprint("demo")
    assert detail["blueprint"]["blueprint_id"] == "demo"
    assert detail["blueprint"]["definition"]["dockerfile"] == "FROM python:3.12"


def test_bundle_blueprint_write_roundtrip_uses_bundle_contract(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))

    created = commander_bundle.create_blueprint(
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

    updated = commander_bundle.update_blueprint("writer", {"description": "Updated", "tags": ["cpu"]})
    assert updated["updated"] is True
    assert updated["blueprint"]["definition"]["description"] == "Updated"
    assert updated["blueprint"]["definition"]["tags"] == ["cpu"]

    exported = commander_bundle.export_blueprint_yaml("writer")
    assert "yaml" in exported
    assert "Writer" in exported["yaml"]

    imported = commander_bundle.import_blueprint_yaml(
        """
id: imported
name: Imported
description: Imported blueprint
dockerfile: FROM alpine:3.20
"""
    )
    assert imported["created"] is True
    assert imported["blueprint"]["blueprint_id"] == "imported"

    deleted = commander_bundle.delete_blueprint("writer")
    assert deleted == {"deleted": True, "blueprint_id": "writer"}


def test_bundle_container_list_gracefully_degrades_without_runtime(monkeypatch):
    def fail_client():
        raise RuntimeError("docker unavailable")

    monkeypatch.setattr(commander_bundle, "get_docker_client", fail_client)
    result = commander_bundle.list_containers()
    assert result["ok"] is False
    assert result["error"]["code"] == "RUNTIME_UNAVAILABLE"


def test_bundle_tool_intents_cover_blueprint_write_tools():
    tool_intents_path = BUNDLE_DIR / "tool_intents.json"
    payload = json.loads(tool_intents_path.read_text(encoding="utf-8"))
    names = {tool["name"] for tool in payload["tools"]}
    assert {
        "blueprint_create",
        "blueprint_update",
        "blueprint_delete",
        "blueprint_import_yaml",
        "blueprint_export_yaml",
    } <= names
    assert {"container_list", "container_inspect", "container_logs", "container_stats", "runtime_quota"} <= names
    assert {"container_exec", "container_exec_detailed"} <= names
    assert {"runtime_cleanup_all", "remove_stopped_container"} <= names
    assert {"network_list", "network_info", "network_cleanup"} <= names
    assert {"proxy_start", "proxy_stop", "proxy_whitelist_get", "proxy_whitelist_set"} <= names
    assert {"dashboard_overview"} <= names
    assert {"host_companion_check", "host_companion_repair", "host_companion_uninstall", "package_manifest_get"} <= names
    assert {"marketplace_bundle_list", "marketplace_starter_list", "marketplace_catalog_list", "marketplace_catalog_sync"} <= names
    assert {"marketplace_starter_install", "marketplace_catalog_install", "marketplace_bundle_export", "marketplace_bundle_import"} <= names
    assert {"volume_list", "volume_get", "volume_remove", "volume_cleanup", "snapshot_list", "snapshot_delete", "snapshot_create", "snapshot_restore"} <= names


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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

    listed = commander_bundle.list_networks()
    assert listed["networks"][0]["name"] == "trion-sandbox"
    detail = commander_bundle.get_network_info("c1")
    assert detail["networks"]["trion-sandbox"]["ip"] == "172.20.0.2"


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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

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
    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

    result = commander_bundle.runtime_quota()

    assert result == {
        "max_containers": 7,
        "max_total_memory_mb": 4096,
        "max_total_cpu": 6.0,
        "containers_used": 1,
        "memory_used_mb": 512,
        "cpu_used": 1.5,
    }


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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())
    monkeypatch.setattr(commander_bundle, "get_blueprint", lambda blueprint_id: {"blueprint": {"definition": {"allowed_exec": ["pwd"]}}})

    simple = commander_bundle.container_exec("c1", "pwd", timeout=5)
    detailed = commander_bundle.container_exec_detailed("c1", "pwd", timeout=5)

    assert simple["exit_code"] == 0
    assert "/workspace" in simple["output"]
    assert detailed["exit_code"] == 0
    assert detailed["stdout"] == "/workspace"
    assert detailed["stderr"] == ""


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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient(managed))
    removed = commander_bundle.remove_stopped_container("c-managed")
    assert removed == {"removed": True, "container_id": "c-managed", "blueprint_id": "demo"}
    assert managed.removed is True

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient(running))
    blocked = commander_bundle.remove_stopped_container("c-running")
    assert blocked == {"removed": False, "container_id": "c-running", "reason": "running"}

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient(unmanaged))
    denied = commander_bundle.remove_stopped_container("c-unmanaged")
    assert denied == {"removed": False, "container_id": "c-unmanaged", "reason": "not_managed"}


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
    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient([iso_empty, iso_used, shared]))

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


def test_bundle_dashboard_view_aggregates_current_slices(monkeypatch):
    monkeypatch.setattr(commander_bundle, "list_containers", lambda: {"containers": [{"status": "running"}, {"status": "exited"}]})
    monkeypatch.setattr(commander_bundle, "list_blueprints", lambda: {"blueprints": [{"blueprint_id": "demo"}]})
    monkeypatch.setattr(commander_bundle, "list_networks", lambda: {"networks": [{"name": "trion-sandbox"}]})
    monkeypatch.setattr(commander_bundle, "list_volumes", lambda: {"volumes": [{"name": "trion_ws_demo"}]})
    monkeypatch.setattr(commander_bundle, "get_whitelist", lambda blueprint_id: {"enabled": True, "domains": []})

    result = commander_bundle.get_dashboard_overview()

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


def test_bundle_marketplace_read_views(monkeypatch, tmp_path):
    marketplace_dir = tmp_path / "marketplace"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = marketplace_dir / "demo.trion-bundle.tar.gz"
    meta = {"id": "demo", "name": "Demo", "version": "1.0.0", "tags": ["starter"], "exported_at": "2026-06-03T12:00:00Z"}
    with tarfile.open(bundle_path, "w:gz") as tar:
        payload = json.dumps(meta).encode("utf-8")
        info = tarfile.TarInfo(name="meta.json")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    monkeypatch.setenv("MARKETPLACE_DIR", str(marketplace_dir))
    monkeypatch.setenv("MARKETPLACE_CATALOG_CACHE", str(marketplace_dir / "catalog_cache.json"))
    commander_bundle._marketplace_views.MARKETPLACE_DIR = str(marketplace_dir)
    commander_bundle._marketplace_views.MARKETPLACE_CATALOG_CACHE = str(marketplace_dir / "catalog_cache.json")

    bundles = commander_bundle.list_bundles()
    assert bundles[0]["id"] == "demo"
    assert commander_bundle.get_starters()[0]["id"] == "python-sandbox"

    index_payload = {
        "schema_version": "1.0.0",
        "blueprints": [
            {
                "id": "remote-demo",
                "name": "Remote Demo",
                "yaml_url": "blueprints/remote-demo.yaml",
                "category": "tools",
                "trusted_level": "verified",
            }
        ],
    }
    monkeypatch.setattr(commander_bundle._marketplace_views, "_http_get_text", lambda url, timeout=20: json.dumps(index_payload))

    synced = commander_bundle.sync_remote_catalog(repo_url="https://github.com/example/catalog", branch="main")
    assert synced["synced"] is True
    catalog = commander_bundle.list_catalog(category="tools", trusted_only=True)
    assert catalog["count"] == 1
    assert catalog["blueprints"][0]["id"] == "remote-demo"


def test_bundle_marketplace_mutations(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    marketplace_dir = tmp_path / "marketplace"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))
    monkeypatch.setenv("MARKETPLACE_DIR", str(marketplace_dir))
    monkeypatch.setenv("MARKETPLACE_CATALOG_CACHE", str(marketplace_dir / "catalog_cache.json"))
    commander_bundle._marketplace_views.MARKETPLACE_DIR = str(marketplace_dir)
    commander_bundle._marketplace_views.MARKETPLACE_CATALOG_CACHE = str(marketplace_dir / "catalog_cache.json")
    commander_bundle._marketplace_mutations.MARKETPLACE_DIR = str(marketplace_dir)

    starter = commander_bundle.install_starter("python-sandbox")
    assert starter["installed"] is True
    blueprint_id = starter["blueprint"]["blueprint_id"]

    filename = commander_bundle.export_bundle(blueprint_id)
    assert filename == f"{blueprint_id}.trion-bundle.tar.gz"
    bundle_bytes = (marketplace_dir / filename).read_bytes()

    imported = commander_bundle.import_bundle(bundle_bytes, filename=filename, overwrite=True)
    assert imported["imported"] is True

    index_payload = {
        "schema_version": "1.0.0",
        "blueprints": [
            {
                "id": "remote-demo",
                "name": "Remote Demo",
                "yaml_url": "blueprints/remote-demo.yaml",
                "category": "tools",
                "trusted_level": "verified",
            }
        ],
    }
    monkeypatch.setattr(
        commander_bundle._marketplace_views,
        "_http_get_text",
        lambda url, timeout=20: json.dumps(index_payload) if url.endswith("index.json") else "id: remote-demo\nname: Remote Demo\nimage: python:3.12\n",
    )
    monkeypatch.setattr(
        commander_bundle._marketplace_mutations,
        "_http_get_text",
        lambda url, timeout=20: "id: remote-demo\nname: Remote Demo\nimage: python:3.12\n",
    )
    commander_bundle.sync_remote_catalog(repo_url="https://github.com/example/catalog", branch="main")
    installed = commander_bundle.install_catalog_blueprint("remote-demo", overwrite=False)
    assert installed["installed"] is True


def test_bundle_volume_views_use_v2_shapes(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz").write_bytes(b"snapshot")
    monkeypatch.setattr(commander_bundle, "SNAPSHOT_DIR", str(snapshot_dir))

    class _FakeVolume:
        def __init__(self):
            self.name = "trion_ws_demo_1"
            self.removed = False
            self.attrs = {
                "Labels": {"trion.managed": "true", "trion.blueprint": "demo", "trion.created": "2026-05-15T10:00:00Z"},
                "CreatedAt": "2026-05-15T10:00:00Z",
                "Driver": "local",
                "Mountpoint": "/var/lib/docker/volumes/demo",
            }

        def remove(self, force=False):
            self.removed = True

    class _FakeVolumes:
        def list(self, filters=None):
            return [_FakeVolume()]

        def get(self, volume_name):
            return _FakeVolume()

    class _FakeClient:
        def __init__(self):
            self.volumes = _FakeVolumes()

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

    listed = commander_bundle.list_volumes()
    assert listed["volumes"][0]["name"] == "trion_ws_demo_1"
    snapshots = commander_bundle.list_snapshots("trion_ws_demo_1")
    assert snapshots["snapshots"][0]["filename"].startswith("trion_ws_demo_1")
    detail = commander_bundle.get_volume("trion_ws_demo_1")
    assert detail["volume"]["driver"] == "local"
    removed = commander_bundle.remove_volume("trion_ws_demo_1")
    assert removed == {"removed": True, "volume": "trion_ws_demo_1"}


def test_bundle_volume_cleanup_respects_dry_run(monkeypatch):
    class _FakeVolume:
        def __init__(self, name):
            self.name = name
            self.removed = False
            self.attrs = {
                "Labels": {"trion.managed": "true"},
                "CreatedAt": "2026-05-15T10:00:00Z",
                "Driver": "local",
                "Mountpoint": f"/volumes/{name}",
            }

        def remove(self):
            self.removed = True

    class _FakeVolumes:
        def __init__(self, volumes):
            self._volumes = list(volumes)

        def list(self, filters=None):
            return list(self._volumes)

    class _FakeContainer:
        def __init__(self):
            self.attrs = {"Mounts": [{"Name": "trion_ws_attached"}]}

    class _FakeContainers:
        def list(self, all=True):
            return [_FakeContainer()]

    class _FakeClient:
        def __init__(self, volumes):
            self.volumes = _FakeVolumes(volumes)
            self.containers = _FakeContainers()

    attached = _FakeVolume("trion_ws_attached")
    orphan = _FakeVolume("trion_ws_orphan")
    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient([attached, orphan]))

    dry_run = commander_bundle.cleanup_orphaned_volumes(dry_run=True)
    assert dry_run == {"orphaned": ["trion_ws_orphan"], "dry_run": True}
    assert orphan.removed is False

    removed = commander_bundle.cleanup_orphaned_volumes(dry_run=False)
    assert removed == {"orphaned": ["trion_ws_orphan"], "dry_run": False}
    assert orphan.removed is True


def test_bundle_snapshot_delete_returns_deleted_flag(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    snapshot_file = snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz"
    snapshot_file.write_bytes(b"snapshot")
    monkeypatch.setattr(commander_bundle, "SNAPSHOT_DIR", str(snapshot_dir))

    deleted = commander_bundle.delete_snapshot(snapshot_file.name)
    assert deleted == {"deleted": True, "filename": snapshot_file.name}
    assert not snapshot_file.exists()

    missing = commander_bundle.delete_snapshot("missing.tar.gz")
    assert missing == {"deleted": False, "filename": "missing.tar.gz"}


def test_bundle_snapshot_create_returns_created_flag(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    monkeypatch.setattr(commander_bundle, "SNAPSHOT_DIR", str(snapshot_dir))

    archive_payload = b"snapshot-bytes"
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as outer_tar:
        info = tarfile.TarInfo(name="snapshot.tar.gz")
        info.size = len(archive_payload)
        outer_tar.addfile(info, io.BytesIO(archive_payload))
    tar_bytes = tar_stream.getvalue()

    class _FakeSnapshotContainer:
        def wait(self, timeout=120):
            return {"StatusCode": 0}

        def get_archive(self, path):
            return [tar_bytes], {"size": len(tar_bytes)}

        def remove(self, force=True):
            return None

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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

    created = commander_bundle.create_snapshot("trion_ws_demo_1", tag="nightly")
    assert created["created"] is True
    assert created["filename"].startswith("trion_ws_demo_1_nightly_")
    assert (snapshot_dir / created["filename"]).read_bytes() == archive_payload


def test_bundle_snapshot_restore_returns_restored_flag(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    snapshot_file = snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz"
    snapshot_file.write_bytes(b"snapshot-bytes")
    monkeypatch.setattr(commander_bundle, "SNAPSHOT_DIR", str(snapshot_dir))

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

    monkeypatch.setattr(commander_bundle, "get_docker_client", lambda: _FakeClient())

    restored = commander_bundle.restore_snapshot(snapshot_file.name, target_volume="trion_ws_restored")
    assert restored == {
        "restored": True,
        "volume": "trion_ws_restored",
        "filename": snapshot_file.name,
    }
