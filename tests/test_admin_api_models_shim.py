from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "adapters" / "admin-api" / "models.py"


def test_admin_api_models_shim_reexports_vendor_models():
    source = PATH.read_text(encoding="utf-8")

    assert 'This is the local truth for the shared commander schema' in source
    assert "class NetworkMode(str, Enum):" in source
    assert "class Blueprint(BaseModel):" in source
    assert "class ContainerInstance(BaseModel):" in source
    assert "from vendor.container_commander.models import *" not in source
