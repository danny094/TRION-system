import io
import tarfile

import container_commander_v2_fakes  # noqa: F401

from volume_views import create_snapshot, delete_snapshot, restore_snapshot  # noqa: E402


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
