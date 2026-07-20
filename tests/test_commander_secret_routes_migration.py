import asyncio
import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"
VENDOR_DIR = ADMIN_API_DIR / "vendor"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_commander_secret_routes_use_truth_store(monkeypatch):
    routes = _load_module("commander_api.secrets")
    from commander_secret_models import SecretEntry, SecretScope

    monkeypatch.setattr(
        routes,
        "list_secrets",
        lambda scope=None, blueprint_id=None: [
            SecretEntry(name="OPENAI_API_KEY", scope=SecretScope.GLOBAL),
        ],
        raising=False,
    )
    monkeypatch.setattr(
        routes,
        "store_secret",
        lambda name, value, scope, blueprint_id=None, expires_at=None: SecretEntry(
            name=name.upper(),
            scope=scope,
            blueprint_id=blueprint_id,
            expires_at=expires_at,
        ),
        raising=False,
    )
    monkeypatch.setattr(routes, "delete_secret", lambda name, scope, blueprint_id=None: True, raising=False)

    # Patch import targets via module globals after reload/imports in functions.
    import commander_secret_store

    monkeypatch.setattr(
        commander_secret_store,
        "list_secrets",
        lambda scope=None, blueprint_id=None: [SecretEntry(name="OPENAI_API_KEY", scope=SecretScope.GLOBAL)],
    )
    monkeypatch.setattr(
        commander_secret_store,
        "store_secret",
        lambda name, value, scope, blueprint_id=None, expires_at=None: SecretEntry(
            name=name.upper(),
            scope=scope,
            blueprint_id=blueprint_id,
            expires_at=expires_at,
        ),
    )
    monkeypatch.setattr(commander_secret_store, "delete_secret", lambda name, scope, blueprint_id=None: True)

    listed = asyncio.run(routes.api_list_secrets())
    stored = asyncio.run(
        routes.api_store_secret(
            _FakeRequest(
                {
                    "name": "openai_api_key",
                    "value": "secret",
                    "scope": "global",
                }
            )
        )
    )
    deleted = asyncio.run(routes.api_delete_secret("OPENAI_API_KEY"))

    assert listed["count"] == 1
    assert listed["secrets"][0]["name"] == "OPENAI_API_KEY"
    assert stored["stored"] is True
    assert stored["secret"]["name"] == "OPENAI_API_KEY"
    assert deleted == {"deleted": True, "name": "OPENAI_API_KEY"}
