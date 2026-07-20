import importlib
import inspect
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


def test_vendor_network_read_paths_delegate_to_mcp(monkeypatch):
    compat = _load_module("commander_network_compat")

    monkeypatch.setattr(compat, "list_networks_via_mcp", lambda: [{"name": "trion-sandbox"}])
    monkeypatch.setattr(
        compat,
        "get_network_info_via_mcp",
        lambda container_id: {"container_id": container_id, "networks": {"trion-sandbox": {"ip": "172.20.0.2"}}},
    )
    monkeypatch.setattr(compat, "cleanup_networks_via_mcp", lambda: ["trion-iso-empty"])

    assert compat.list_networks() == [{"name": "trion-sandbox"}]
    assert compat.get_network_info("c1") == {
        "container_id": "c1",
        "networks": {"trion-sandbox": {"ip": "172.20.0.2"}},
    }
    assert compat.cleanup_networks() == ["trion-iso-empty"]


def test_vendor_network_resolution_delegates_to_local_deploy_truth(monkeypatch):
    compat = _load_module("commander_network_compat")

    monkeypatch.setattr(compat, "ensure_shared_network_local", lambda: "trion-sandbox")
    monkeypatch.setattr(
        compat,
        "resolve_network_local",
        lambda mode, container_name="": {"network": "bridge", "requires_approval": False, "mode": str(mode)},
    )

    assert compat.ensure_shared_network() == "trion-sandbox"
    assert compat.resolve_network("bridge", "c1") == {
        "network": "bridge",
        "requires_approval": False,
        "mode": "bridge",
    }
