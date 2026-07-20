from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_TRUTH = ROOT / "adapters" / "admin-api" / "commander_hardware_resolution.py"


def test_local_hardware_truth_exposes_empty_resolution_builder():
    source = LOCAL_TRUTH.read_text(encoding="utf-8")

    assert "def empty_hardware_resolution(" in source
