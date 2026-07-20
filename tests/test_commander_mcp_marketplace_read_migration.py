import asyncio
import importlib
import json
import sys
import tarfile
from io import BytesIO
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
    def __init__(self, payload):
        self._payload = payload
        self.headers = {"content-type": "application/json"}

    async def json(self):
        return self._payload


def test_marketplace_read_routes_use_mcp_runtime_helpers(monkeypatch):
    routes = _load_module("commander_api.operations")
    bundles = {"bundles": [{"filename": "demo.trion-bundle.tar.gz"}], "count": 1}
    starters = {"starters": [{"id": "python-sandbox"}], "count": 1}
    catalog = {"blueprints": [{"id": "demo"}], "count": 1, "category": "all", "trusted_only": False}
    synced = {"synced": True, "count": 1}
    monkeypatch.setattr(routes, "list_marketplace_bundles_via_mcp", lambda: bundles, raising=False)
    monkeypatch.setattr(routes, "list_marketplace_starters_via_mcp", lambda: starters, raising=False)
    monkeypatch.setattr(
        routes,
        "list_marketplace_catalog_via_mcp",
        lambda category="", trusted_only=False: catalog,
        raising=False,
    )
    monkeypatch.setattr(
        routes,
        "sync_marketplace_catalog_via_mcp",
        lambda repo_url="", branch="main": synced,
        raising=False,
    )

    assert asyncio.run(routes.api_list_bundles()) == bundles
    assert asyncio.run(routes.api_list_starters()) == starters
    assert asyncio.run(routes.api_marketplace_catalog()) == catalog
    assert asyncio.run(routes.api_marketplace_catalog_sync(_FakeRequest({"repo_url": "https://github.com/x/y", "branch": "main"}))) == synced


def test_operations_slice_no_longer_imports_vendor_marketplace_for_read_paths():
    source = (ADMIN_API_DIR / "commander_api" / "operations.py").read_text()
    assert "from container_commander.marketplace import list_bundles" not in source
    assert "from container_commander.marketplace import get_starters" not in source
    assert "from container_commander.marketplace import list_catalog" not in source
    assert "from container_commander.marketplace import sync_remote_catalog" not in source


def test_marketplace_views_bundle_and_catalog_read(tmp_path, monkeypatch):
    server_dir = ROOT / "mcp-servers" / "container-commander"
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))
    import marketplace_views

    marketplace_dir = tmp_path / "marketplace"
    monkeypatch.setenv("MARKETPLACE_DIR", str(marketplace_dir))
    monkeypatch.setenv("MARKETPLACE_CATALOG_CACHE", str(marketplace_dir / "catalog_cache.json"))
    marketplace_views.MARKETPLACE_DIR = str(marketplace_dir)
    marketplace_views.MARKETPLACE_CATALOG_CACHE = str(marketplace_dir / "catalog_cache.json")

    marketplace_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = marketplace_dir / "demo.trion-bundle.tar.gz"
    meta = {"id": "demo", "name": "Demo", "version": "1.0.0", "tags": ["starter"], "exported_at": "2026-06-03T12:00:00Z"}
    with tarfile.open(bundle_path, "w:gz") as tar:
        payload = json.dumps(meta).encode("utf-8")
        info = tarfile.TarInfo(name="meta.json")
        info.size = len(payload)
        tar.addfile(info, BytesIO(payload))

    bundles = marketplace_views.list_bundles()
    assert bundles[0]["id"] == "demo"

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
    monkeypatch.setattr(marketplace_views, "_http_get_text", lambda url, timeout=20: json.dumps(index_payload))

    synced = marketplace_views.sync_remote_catalog(repo_url="https://github.com/example/catalog", branch="main")
    assert synced["synced"] is True
    catalog = marketplace_views.list_catalog(category="tools", trusted_only=True)
    assert catalog["count"] == 1
    assert catalog["blueprints"][0]["id"] == "remote-demo"
