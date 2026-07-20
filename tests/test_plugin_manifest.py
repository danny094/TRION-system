import io
import json
import zipfile
from pathlib import Path

from plugins.manifest import extract_plugin_archive, load_plugin_manifest


def test_load_plugin_manifest_accepts_launchpad_app(tmp_path: Path):
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "plugin.json").write_text(
        json.dumps(
            {
                "id": "container-ui",
                "name": "Container UI",
                "version": "1.0.0",
                "kind": "app",
                "mount": "launchpad",
                "entry": "index.html",
            }
        ),
        encoding="utf-8",
    )
    manifest = load_plugin_manifest(root)
    assert manifest["id"] == "container-ui"
    assert manifest["entry"] == "index.html"


def test_extract_plugin_archive_finds_nested_plugin_json(tmp_path, monkeypatch):
    monkeypatch.setattr("plugins.manifest._TMP_DIR", tmp_path)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as bundle:
        bundle.writestr("container-ui/plugin.json", json.dumps(
            {
                "id": "container-ui",
                "name": "Container UI",
                "version": "1.0.0",
                "kind": "app",
                "mount": "launchpad",
                "entry": "index.html",
            }
        ))
        bundle.writestr("container-ui/index.html", "<html></html>")
    root, manifest = extract_plugin_archive("container-ui.zip", payload.getvalue())
    assert root.name == "container-ui"
    assert manifest["mount"] == "launchpad"


def test_load_plugin_manifest_normalizes_permissions(tmp_path: Path):
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "plugin.json").write_text(
        json.dumps(
            {
                "id": "container-ui",
                "name": "Container UI",
                "version": "1.0.0",
                "kind": "app",
                "mount": "launchpad",
                "entry": "index.html",
                "permissions": {
                    "api": ["/api/tools*", "/health"],
                    "tools": ["time_now"],
                    "events": ["task_loop_state"],
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = load_plugin_manifest(root)
    assert manifest["permissions"]["api"] == ["/api/tools*", "/health"]
    assert manifest["permissions"]["tools"] == ["time_now"]


def test_load_plugin_manifest_rejects_invalid_permissions(tmp_path: Path):
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "plugin.json").write_text(
        json.dumps(
            {
                "id": "container-ui",
                "name": "Container UI",
                "version": "1.0.0",
                "kind": "app",
                "mount": "launchpad",
                "entry": "index.html",
                "permissions": ["not-an-object"],
            }
        ),
        encoding="utf-8",
    )
    try:
        load_plugin_manifest(root)
    except Exception as exc:
        assert "permissions" in str(exc)
        return
    raise AssertionError("Expected invalid permissions to be rejected")
