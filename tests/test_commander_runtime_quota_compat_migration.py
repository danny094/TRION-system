from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_runtime_quota_compat.py"


def test_commander_runtime_quota_compat_is_local_truth_for_quota_wrappers():
    source = PATH.read_text(encoding="utf-8")

    assert "from commander_deploy_runtime_state import (" in source
    assert "RuntimeStateRefs" in source
    assert "reserve_quota" in source
    assert "release_quota_reservation" in source
    assert "def get_quota(state: RuntimeStateRefs):" in source
    assert "def check_quota(resources, state: RuntimeStateRefs) -> None:" in source
