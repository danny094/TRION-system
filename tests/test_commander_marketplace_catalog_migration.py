from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "adapters" / "admin-api" / "commander_marketplace_catalog.py"


def test_commander_marketplace_catalog_is_local_truth_for_remote_catalog():
    source = CATALOG_PATH.read_text(encoding="utf-8")

    assert "def http_get_text(" in source
    assert "def http_get_bytes(" in source
    assert "def resolve_github_raw(" in source
    assert "def default_catalog_repo_from_settings(" in source
    assert "def normalize_catalog_entry(" in source
    assert "def load_catalog_cache(" in source
    assert "def save_catalog_cache(" in source
    assert "def sync_remote_catalog(" in source
    assert "def get_catalog_cache(" in source
    assert "def list_catalog(" in source
