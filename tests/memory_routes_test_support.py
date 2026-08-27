import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _resolve_admin_api_dir() -> Path:
    candidates = [
        ROOT / "adapters" / "admin-api",
        Path("/app"),
        ROOT,
    ]
    for path in candidates:
        if (path / "memory_routes.py").exists():
            return path
    raise FileNotFoundError("memory_routes.py not found in any known layout")


ADMIN_API_DIR = _resolve_admin_api_dir()


def _load_memory_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_memory_routes_for_test",
        ADMIN_API_DIR / "memory_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _json(response):
    return json.loads(response.body.decode("utf-8"))
