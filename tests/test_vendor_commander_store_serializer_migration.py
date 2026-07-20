from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "adapters" / "admin-api" / "commander_blueprint_serializer.py"


def test_local_blueprint_serializer_exists_as_truth():
    source = LOCAL.read_text(encoding="utf-8")

    assert "def row_to_blueprint(" in source
    assert "def blueprint_to_params(" in source
