import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_local_blueprint_yaml_uses_local_write_and_read_truths(monkeypatch):
    module = _load_module("commander_blueprint_yaml")

    class _Blueprint:
        id = "bp1"

    monkeypatch.setattr(module, "import_blueprint_yaml", lambda yaml_content: {"blueprint": {"blueprint_id": "bp1"}}, raising=False)
    monkeypatch.setattr(module, "get_blueprint", lambda blueprint_id: _Blueprint() if blueprint_id == "bp1" else None, raising=False)
    monkeypatch.setattr(module, "export_blueprint_yaml", lambda blueprint_id: {"yaml": "id: bp1\nname: Demo\n"}, raising=False)

    imported = module.import_from_yaml("id: bp1\nname: Demo\n")
    exported = module.export_to_yaml("bp1")

    assert imported.id == "bp1"
    assert exported == "id: bp1\nname: Demo\n"

