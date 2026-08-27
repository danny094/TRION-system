from container_commander_bundle_fakes import _init_blueprint_db
import bundle_common  # noqa: E402
import bundle_docker  # noqa: E402
import server as commander_bundle  # noqa: E402


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


def test_bundle_volume_views_use_v2_shapes(monkeypatch, tmp_path):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "trion_ws_demo_1_20260602_120000.tar.gz").write_bytes(b"snapshot")
    monkeypatch.setattr(bundle_common, "SNAPSHOT_DIR", str(snapshot_dir))

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

    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient())

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
    monkeypatch.setattr(bundle_docker, "get_docker_client", lambda: _FakeClient([attached, orphan]))

    dry_run = commander_bundle.cleanup_orphaned_volumes(dry_run=True)
    assert dry_run == {"orphaned": ["trion_ws_orphan"], "dry_run": True}
    assert orphan.removed is False

    removed = commander_bundle.cleanup_orphaned_volumes(dry_run=False)
    assert removed == {"orphaned": ["trion_ws_orphan"], "dry_run": False}
    assert orphan.removed is True
