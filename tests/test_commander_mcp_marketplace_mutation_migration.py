import asyncio
import base64
import importlib
import io
import json
import sys
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


class _FakeRequest:
    def __init__(self, payload=None, raw: bytes = b""):
        self._payload = payload
        self._raw = raw
        self.headers = {"content-type": "application/json"} if payload is not None else {}

    async def json(self):
        return self._payload or {}

    async def body(self):
        return self._raw


def test_marketplace_mutation_routes_use_mcp_runtime_helpers(monkeypatch):
    routes = _load_module("commander_api.operations")
    monkeypatch.setattr(routes, "install_marketplace_catalog_blueprint_via_mcp", lambda blueprint_id, overwrite=False: {"installed": True}, raising=False)
    monkeypatch.setattr(routes, "install_marketplace_starter_via_mcp", lambda starter_id: {"installed": True}, raising=False)
    monkeypatch.setattr(routes, "export_marketplace_bundle_via_mcp", lambda blueprint_id: {"exported": True, "filename": "demo.trion-bundle.tar.gz"}, raising=False)
    monkeypatch.setattr(routes, "import_marketplace_bundle_via_mcp", lambda body, filename="", overwrite=False: {"imported": True}, raising=False)

    assert asyncio.run(routes.api_marketplace_catalog_install("demo", _FakeRequest({"overwrite": True}))) == {"installed": True}
    assert asyncio.run(routes.api_install_starter("python-sandbox")) == {"installed": True}
    assert asyncio.run(routes.api_export_bundle("demo")) == {"exported": True, "filename": "demo.trion-bundle.tar.gz"}
    assert asyncio.run(routes.api_import_bundle(_FakeRequest(raw=b"bundle"))) == {"imported": True}


def test_operations_slice_no_longer_imports_vendor_marketplace_for_mutations():
    source = (ADMIN_API_DIR / "commander_api" / "operations.py").read_text()
    assert "from container_commander.marketplace import install_catalog_blueprint" not in source
    assert "from container_commander.marketplace import install_starter" not in source
    assert "from container_commander.marketplace import export_bundle" not in source
    assert "from container_commander.marketplace import import_bundle" not in source


def test_marketplace_mutations_install_export_import(tmp_path, monkeypatch):
    server_dir = ROOT / "mcp-servers" / "container-commander"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))
    import marketplace_mutations
    import marketplace_views

    db_path = tmp_path / "commander.db"
    marketplace_dir = tmp_path / "marketplace"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))
    monkeypatch.setenv("MARKETPLACE_DIR", str(marketplace_dir))
    monkeypatch.setenv("MARKETPLACE_CATALOG_CACHE", str(marketplace_dir / "catalog_cache.json"))
    marketplace_views.MARKETPLACE_DIR = str(marketplace_dir)
    marketplace_views.MARKETPLACE_CATALOG_CACHE = str(marketplace_dir / "catalog_cache.json")
    marketplace_mutations.MARKETPLACE_DIR = str(marketplace_dir)

    starter = marketplace_mutations.install_starter("python-sandbox")
    assert starter["installed"] is True
    blueprint_id = starter["blueprint"]["blueprint_id"]

    filename = marketplace_mutations.export_bundle(blueprint_id)
    assert filename == f"{blueprint_id}.trion-bundle.tar.gz"
    bundle_bytes = (marketplace_dir / filename).read_bytes()

    imported = marketplace_mutations.import_bundle(bundle_bytes, filename=filename, overwrite=True)
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
    monkeypatch.setattr(marketplace_views, "_http_get_text", lambda url, timeout=20: json.dumps(index_payload) if url.endswith("index.json") else "id: remote-demo\nname: Remote Demo\nimage: python:3.12\n")
    monkeypatch.setattr(marketplace_mutations, "_http_get_text", lambda url, timeout=20: "id: remote-demo\nname: Remote Demo\nimage: python:3.12\n")
    marketplace_views.sync_remote_catalog(repo_url="https://github.com/example/catalog", branch="main")
    installed = marketplace_mutations.install_catalog_blueprint("remote-demo", overwrite=False)
    assert installed["installed"] is True
