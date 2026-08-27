from container_commander_v2_fakes import _FakeContainer, _FakeVolume, _FakeVolumes

from volume_views import cleanup_orphaned_volumes, get_volume, list_snapshots, list_volumes, remove_volume  # noqa: E402


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
