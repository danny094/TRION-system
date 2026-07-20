import asyncio
import importlib
import sys
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


def test_proxy_routes_use_mcp_runtime_helpers(monkeypatch):
    routes = _load_module("commander_api.operations")

    monkeypatch.setattr(routes, "start_proxy_via_mcp", lambda: True, raising=False)
    monkeypatch.setattr(routes, "stop_proxy_via_mcp", lambda: True, raising=False)
    monkeypatch.setattr(routes, "get_proxy_whitelist_via_mcp", lambda blueprint_id: ["example.com"], raising=False)
    monkeypatch.setattr(routes, "set_proxy_whitelist_via_mcp", lambda blueprint_id, domains: True, raising=False)

    started = asyncio.run(routes.api_start_proxy())
    stopped = asyncio.run(routes.api_stop_proxy())
    listed = asyncio.run(routes.api_get_whitelist("bp-demo"))
    updated = asyncio.run(routes.api_set_whitelist("bp-demo", _FakeRequest({"domains": ["example.com"]})))

    assert started == {"started": True}
    assert stopped == {"stopped": True}
    assert listed == {"blueprint_id": "bp-demo", "domains": ["example.com"]}
    assert updated == {"updated": True, "blueprint_id": "bp-demo", "domains": ["example.com"]}


def test_operations_slice_no_longer_imports_vendor_proxy_package():
    source = (ADMIN_API_DIR / "commander_api" / "operations.py").read_text()

    assert "from container_commander.proxy import ensure_proxy_running" not in source
    assert "from container_commander.proxy import stop_proxy" not in source
    assert "from container_commander.proxy import get_whitelist" not in source
    assert "from container_commander.proxy import set_whitelist" not in source
