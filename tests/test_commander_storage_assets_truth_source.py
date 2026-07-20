import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_storage_assets_truth_roundtrip_is_local(monkeypatch, tmp_path):
    assets_path = tmp_path / "storage_assets.json"
    monkeypatch.setenv("COMMANDER_STORAGE_ASSETS_PATH", str(assets_path))

    sys.modules.pop("commander_storage_assets_store", None)

    truth = _load_module("commander_storage_assets_store")

    stored = truth.upsert_asset(
        "media",
        {
            "path": str(tmp_path / "library"),
            "label": "Library",
            "default_mode": "ro",
            "allowed_for": ["media", "workspace", "invalid"],
            "published_to_commander": True,
        },
    )
    assert stored["id"] == "media"
    assert truth.get_asset("media")["label"] == "Library"
    assert truth.list_assets(published_only=True)["media"]["default_mode"] == "ro"
    assert truth.delete_asset("media") is True
    assert truth.get_asset("media") is None


def test_storage_route_reads_assets_from_truth_module():
    source = (ADMIN_API_DIR / "commander_api" / "storage.py").read_text(encoding="utf-8")
    assert "from commander_storage_assets_store import list_assets" in source
    assert "from commander_storage_assets_store import get_asset" in source
    assert "from commander_storage_assets_store import upsert_asset" in source
    assert "from commander_storage_assets_store import delete_asset" in source
    assert "from container_commander.storage_assets import list_assets" not in source


def test_vendor_storage_assets_namespace_is_removed():
    assert not (ADMIN_API_DIR / "vendor" / "container_commander" / "storage_assets.py").exists()
