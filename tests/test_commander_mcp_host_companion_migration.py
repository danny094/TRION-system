import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _ensure_admin_api_path() -> None:
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))


def _load_module(name: str):
    _ensure_admin_api_path()
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_host_companion_mcp_runtime_helpers(monkeypatch):
    mcp_runtime = _load_module("commander_api.mcp_runtime")

    monkeypatch.setattr(
        mcp_runtime,
        "call_commander_runtime_tool",
        lambda tool_name, arguments=None, timeout=5.0: {
            "host_companion_check": {"checked": True, "configured": False},
            "host_companion_repair": {"repaired": False, "reason": "host_companion_runtime_not_implemented_in_v2"},
            "host_companion_uninstall": {"uninstalled": False, "reason": "host_companion_runtime_not_implemented_in_v2"},
            "package_manifest_get": {"manifest": {"host_companion": {"enabled": True}}},
        }[tool_name],
        raising=False,
    )

    checked = mcp_runtime.check_host_companion_via_mcp("bp-demo")
    repaired = mcp_runtime.repair_host_companion_via_mcp("bp-demo")
    uninstalled = mcp_runtime.uninstall_host_companion_via_mcp("bp-demo")
    manifest = mcp_runtime.get_package_manifest_via_mcp("bp-demo")

    assert checked["checked"] is True
    assert repaired["reason"] == "host_companion_runtime_not_implemented_in_v2"
    assert uninstalled["reason"] == "host_companion_runtime_not_implemented_in_v2"
    assert manifest == {"host_companion": {"enabled": True}}
