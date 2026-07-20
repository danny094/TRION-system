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


def test_commander_audit_store_reads_and_filters_entries(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))
    store = _load_module("commander_audit_store")

    store.log_action("c1", "bp-1", "start", "image=demo")
    store.log_action("c2", "bp-2", "stop", "")

    entries = store.get_audit_log(limit=10)
    assert len(entries) == 2
    assert entries[0]["action"] in {"start", "stop"}

    filtered = store.get_audit_log(blueprint_id="bp-1", limit=10)
    assert len(filtered) == 1
    assert filtered[0]["blueprint_id"] == "bp-1"
    assert filtered[0]["action"] == "start"


def test_commander_audit_route_uses_truth_module(monkeypatch, tmp_path):
    db_path = tmp_path / "commander.db"
    monkeypatch.setenv("COMMANDER_DB_PATH", str(db_path))
    audit = _load_module("commander_api.audit")
    store = _load_module("commander_audit_store")

    store.log_action("c1", "bp-1", "start", "image=demo")

    payload = asyncio.run(audit.api_audit_log(blueprint_id="bp-1", limit=10))
    assert payload["count"] == 1
    assert payload["entries"][0]["blueprint_id"] == "bp-1"


def test_commander_audit_route_no_longer_imports_vendor_store():
    audit_source = (ADMIN_API_DIR / "commander_api" / "audit.py").read_text(encoding="utf-8")
    assert "from commander_audit_store import get_audit_log" in audit_source
    assert "from container_commander.store import get_audit_log" not in audit_source
