from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_exec_policy.py"


def test_commander_exec_policy_is_local_truth_for_policy_violation_error():
    source = PATH.read_text(encoding="utf-8")

    assert "class PolicyViolationError(Exception):" in source
    assert "policy_denied:" in source
    assert "allowed_exec" in source
