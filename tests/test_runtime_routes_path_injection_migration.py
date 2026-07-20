from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROUTES_PATH = ROOT / "adapters" / "admin-api" / "runtime_routes.py"


def test_runtime_routes_no_longer_injects_repo_root_into_sys_path_for_digest_state():
    source = RUNTIME_ROUTES_PATH.read_text(encoding="utf-8")

    assert "sys.path.insert" not in source
    assert "_root = os.path.dirname" not in source
    assert 'importlib.import_module("core.digest.runtime_state")' in source
