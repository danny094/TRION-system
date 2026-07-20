from pathlib import Path

import pytest

from utils.routing import ollama_manager


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "utils" / "routing" / "ollama_manager.py"


def test_ollama_manager_no_longer_imports_container_commander_engine():
    source = PATH.read_text(encoding="utf-8")

    assert "from container_commander.engine import get_client" not in source
    assert "docker.from_env()" in source


def test_ollama_manager_docker_client_raises_dependency_error_when_sdk_missing(monkeypatch):
    monkeypatch.setattr(ollama_manager, "docker", None)
    monkeypatch.setattr(ollama_manager, "_docker_client_singleton", None)

    with pytest.raises(ollama_manager.ComputeDependencyError, match="Docker unavailable"):
        ollama_manager._docker_client()
