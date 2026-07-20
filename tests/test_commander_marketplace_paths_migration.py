from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_marketplace_paths.py"


def test_commander_marketplace_paths_is_local_truth_for_marketplace_roots():
    source = PATH.read_text(encoding="utf-8")

    assert "MARKETPLACE_DIR = os.environ.get(" in source
    assert "MARKETPLACE_CATALOG_CACHE = os.environ.get(" in source
    assert "REPO_ROOT = Path(__file__).resolve().parents[1]" in source
    assert 'LOCAL_PACKAGE_DIR = REPO_ROOT / "marketplace" / "packages"' in source
    assert 'LOCAL_CONTAINER_ADDONS_DIR = REPO_ROOT / "intelligence_modules" / "container_addons"' in source
    assert "def resolve_container_addon_install_root(" in source
