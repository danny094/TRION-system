from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = ROOT / "adapters" / "admin-api" / "commander_marketplace_bundle.py"


def test_commander_marketplace_bundle_is_local_truth_for_bundle_paths():
    source = BUNDLE_PATH.read_text(encoding="utf-8")

    assert "def export_bundle(" in source
    assert "def import_bundle(" in source
    assert "def list_bundles(" in source
    assert "def install_catalog_blueprint(" in source
    assert "def _add_string_to_tar(" in source
    assert "def _ensure_marketplace_dir(" in source
    assert "def _convert_env_secrets(" in source
    assert "def _load_local_package_manifest(" in source
    assert "def _install_bundle_package(" in source
    assert "def _install_bundle_container_addons(" in source
