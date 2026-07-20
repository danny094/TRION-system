import importlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_module(name: str):
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    module = importlib.import_module(name)
    return importlib.reload(module)


def test_home_note_memory_roundtrip(monkeypatch, tmp_path):
    module = _load_module("home_note_memory")
    monkeypatch.setenv("TRION_HOME_NOTE_MEMORY_PATH", str(tmp_path / "home-note-memory.json"))
    module = importlib.reload(module)

    saved = module.remember_note(content="Alpha note", category="note", identity_path="/home/trion")
    assert saved["saved"] is True
    assert saved["entry"]["content"] == "Alpha note"

    recent = module.recent_notes(identity_path="/home/trion")
    assert recent["count"] == 1
    assert recent["entries"][0]["content"] == "Alpha note"

    recalled = module.recall_notes(query="alpha", identity_path="/home/trion")
    assert recalled["count"] == 1
    assert recalled["entries"][0]["id"] == saved["entry"]["id"]

    status = module.memory_status(identity_path="/home/trion")
    assert status["status"] == "ready"
    assert status["count"] == 1
    assert status["identity_path"] == "/home/trion"


def test_home_note_memory_separates_identity_paths(monkeypatch, tmp_path):
    module = _load_module("home_note_memory")
    monkeypatch.setenv("TRION_HOME_NOTE_MEMORY_PATH", str(tmp_path / "home-note-memory.json"))
    module = importlib.reload(module)

    module.remember_note(content="Home A", identity_path="/home/a")
    module.remember_note(content="Home B", identity_path="/home/b")

    recent_a = module.recent_notes(identity_path="/home/a")
    recent_b = module.recent_notes(identity_path="/home/b")

    assert recent_a["count"] == 1
    assert recent_a["entries"][0]["content"] == "Home A"
    assert recent_b["count"] == 1
    assert recent_b["entries"][0]["content"] == "Home B"


def test_home_note_memory_rejects_empty_content(monkeypatch, tmp_path):
    module = _load_module("home_note_memory")
    monkeypatch.setenv("TRION_HOME_NOTE_MEMORY_PATH", str(tmp_path / "home-note-memory.json"))
    module = importlib.reload(module)

    with pytest.raises(module.MemoryPolicyError) as exc:
        module.remember_note(content="   ")

    assert exc.value.error_code == "bad_request"
