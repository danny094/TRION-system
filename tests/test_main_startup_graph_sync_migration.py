import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"
VENDOR_PACKAGE_DIR = VENDOR_DIR / "container_commander"
MAIN = ADMIN_API_DIR / "main.py"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    if str(VENDOR_PACKAGE_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_PACKAGE_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_main_startup_uses_local_graph_sync_truth():
    source = MAIN.read_text()

    assert "from commander_blueprint_graph_sync import sync_blueprints_to_graph" in source
    assert "from store.graph_sync import sync_blueprints_to_graph" not in source


def test_local_graph_sync_uses_local_blueprint_listing():
    graph_sync = _load_module("commander_blueprint_graph_sync")
    source = (ADMIN_API_DIR / "commander_blueprint_graph_sync.py").read_text()

    assert "from commander_deploy_blueprints import ensure_store_initialized, list_blueprints" in source
    assert "from store.crud import list_blueprints" not in source
    assert callable(graph_sync.sync_blueprints_to_graph)
