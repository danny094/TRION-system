import asyncio
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


class _FakeRequest:
    def __init__(self, payload, content_type: str = "application/json"):
        self._payload = payload
        self.headers = {"content-type": content_type}

    async def json(self):
        return self._payload


def test_approval_routes_use_local_truth_modules(monkeypatch):
    routes = _load_module("commander_api.operations")

    monkeypatch.setattr(routes, "get_pending", lambda: [{"id": "a1"}], raising=False)
    monkeypatch.setattr(routes, "get_history", lambda limit=20: [{"id": "h1"}], raising=False)
    monkeypatch.setattr(routes, "get_approval", lambda approval_id: {"id": approval_id}, raising=False)
    monkeypatch.setattr(
        routes,
        "approve",
        lambda approval_id, approved_by="user": {"container_id": "c1", "approval_id": approval_id},
        raising=False,
    )
    monkeypatch.setattr(routes, "reject", lambda approval_id, rejected_by="user", reason="": True, raising=False)

    pending = asyncio.run(routes.api_get_pending_approvals())
    history = asyncio.run(routes.api_approval_history(limit=10))
    approval = asyncio.run(routes.api_get_approval("a1"))
    approved = asyncio.run(routes.api_approve("a1"))
    rejected = asyncio.run(routes.api_reject("a1", _FakeRequest({"reason": "nope"})))

    assert pending == {"approvals": [{"id": "a1"}], "count": 1}
    assert history == {"history": [{"id": "h1"}], "count": 1}
    assert approval == {"id": "a1"}
    assert approved == {"approved": True, "container": {"container_id": "c1", "approval_id": "a1"}}
    assert rejected == {"rejected": True, "approval_id": "a1"}

def test_operations_slice_no_longer_imports_vendor_approval_package():
    source = (ADMIN_API_DIR / "commander_api" / "operations.py").read_text()

    assert "from container_commander.approval import get_pending" not in source
    assert "from container_commander.approval import get_history" not in source
    assert "from container_commander.approval import get_approval" not in source
    assert "from container_commander.approval import approve" not in source
    assert "from container_commander.approval import reject" not in source


def test_vendor_approval_namespace_is_removed():
    approval_dir = ADMIN_API_DIR / "vendor" / "container_commander" / "approval"
    remaining = [path.name for path in approval_dir.glob("*.py")]
    assert remaining == []
