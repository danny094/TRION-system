from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DEFAULTS_PATH = ROOT / "adapters" / "admin-api" / "memory_defaults_routes.py"
AUTONOMY_PROFILE_PATH = ROOT / "adapters" / "admin-api" / "autonomy_profile_routes.py"


def test_memory_defaults_routes_no_longer_injects_own_directory_into_sys_path():
    source = MEMORY_DEFAULTS_PATH.read_text(encoding="utf-8")

    assert "sys.path.insert" not in source
    assert "_CURRENT_DIR" not in source
    assert "import sys" not in source
    assert "from utils.memory_defaults import (" in source


def test_autonomy_profile_routes_no_longer_injects_own_directory_into_sys_path():
    source = AUTONOMY_PROFILE_PATH.read_text(encoding="utf-8")

    assert "sys.path.insert" not in source
    assert "_CURRENT_DIR" not in source
    assert "import sys" not in source
    assert "from autonomy_profile_mapping import build_runtime_overrides" in source
