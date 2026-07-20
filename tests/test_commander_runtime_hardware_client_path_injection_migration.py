from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "commander_runtime_hardware_client.py"


def test_runtime_hardware_client_no_longer_injects_support_dir_into_sys_path():
    source = PATH.read_text(encoding="utf-8")

    assert "sys.path.insert" not in source
    assert "spec_from_file_location(" in source
    assert '"runtime_hardware"' in source
    assert 'importlib.import_module("runtime_hardware.connectors")' in source
    assert 'importlib.import_module("runtime_hardware.models")' in source
