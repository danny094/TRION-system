import io
import json
import tarfile

from container_commander_bundle_fakes import BUNDLE_DIR
import bundle_view_loader  # noqa: E402
import server as commander_bundle  # noqa: E402


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


def test_bundle_dashboard_view_aggregates_current_slices(monkeypatch):
    monkeypatch.setattr(bundle_view_loader._dashboard_views, "list_containers", lambda: {"containers": [{"status": "running"}, {"status": "exited"}]})
    monkeypatch.setattr(bundle_view_loader._dashboard_views, "list_blueprints", lambda: {"blueprints": [{"blueprint_id": "demo"}]})
    monkeypatch.setattr(bundle_view_loader._dashboard_views, "list_networks", lambda: {"networks": [{"name": "trion-sandbox"}]})
    monkeypatch.setattr(bundle_view_loader._dashboard_views, "list_volumes", lambda: {"volumes": [{"name": "trion_ws_demo"}]})
    monkeypatch.setattr(bundle_view_loader._dashboard_views, "get_whitelist", lambda blueprint_id: {"enabled": True, "domains": []})

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
    bundle_view_loader._marketplace_views.MARKETPLACE_DIR = str(marketplace_dir)
    bundle_view_loader._marketplace_views.MARKETPLACE_CATALOG_CACHE = str(marketplace_dir / "catalog_cache.json")
    bundle_view_loader._marketplace_mutations.MARKETPLACE_DIR = str(marketplace_dir)
    monkeypatch.setattr(bundle_view_loader._marketplace_mutations, "get_starters", bundle_view_loader._marketplace_views.get_starters)
    monkeypatch.setattr(bundle_view_loader._marketplace_mutations, "list_catalog", bundle_view_loader._marketplace_views.list_catalog)

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
        bundle_view_loader._marketplace_views,
        "_http_get_text",
        lambda url, timeout=20: json.dumps(index_payload) if url.endswith("index.json") else "id: remote-demo\nname: Remote Demo\nimage: python:3.12\n",
    )
    monkeypatch.setattr(
        bundle_view_loader._marketplace_mutations,
        "_http_get_text",
        lambda url, timeout=20: "id: remote-demo\nname: Remote Demo\nimage: python:3.12\n",
    )
    commander_bundle.sync_remote_catalog(repo_url="https://github.com/example/catalog", branch="main")
    installed = commander_bundle.install_catalog_blueprint("remote-demo", overwrite=False)
    assert installed["installed"] is True
