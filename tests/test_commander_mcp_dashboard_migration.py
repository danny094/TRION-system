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


def test_dashboard_route_uses_mcp_runtime_helper(monkeypatch):
    routes = _load_module("commander_api.operations")
    payload = {
        "health": {"runtime": "ok", "blueprint_store": "ok", "proxy_policy": "disabled"},
        "resources": {"containers": {"total": 1, "running": 1, "stopped": 0}},
        "alerts": [],
        "events": [],
    }
    monkeypatch.setattr(routes, "get_dashboard_overview_via_mcp", lambda: payload, raising=False)

    result = asyncio.run(routes.api_dashboard())

    assert result == payload


def test_operations_slice_no_longer_imports_vendor_dashboard_package():
    source = (ADMIN_API_DIR / "commander_api" / "operations.py").read_text()

    assert "from container_commander.dashboard import get_dashboard_overview" not in source
