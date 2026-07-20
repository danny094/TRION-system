import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import mcp.installer_registry as installer_registry
from mcp.installer_common import load_custom_config, save_custom_config


class _ObservableRLock:
    def __init__(self, roles, second_attempted):
        self._lock = threading.RLock()
        self._roles = roles
        self._second_attempted = second_attempted

    def __enter__(self):
        if getattr(self._roles, "name", None) == "second":
            self._second_attempted.set()
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._lock.release()


def test_registry_rmw_serializes_without_lost_update(monkeypatch, tmp_path):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    roles = threading.local()
    first_in_write = threading.Event()
    release_first = threading.Event()
    second_attempted = threading.Event()
    monkeypatch.setattr(
        installer_registry,
        "REGISTRY_LOCK",
        _ObservableRLock(roles, second_attempted),
    )
    real_write = installer_registry._write_registry

    def gated_write(registry):
        if getattr(roles, "name", None) == "first":
            first_in_write.set()
            assert release_first.wait(timeout=2)
        real_write(registry)

    monkeypatch.setattr(installer_registry, "_write_registry", gated_write)

    def upsert(role, name):
        roles.name = role
        installer_registry.upsert_registry_entry(name, {"enabled": True})

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(upsert, "first", "alpha")
        assert first_in_write.wait(timeout=2)
        second = pool.submit(upsert, "second", "beta")
        assert second_attempted.wait(timeout=2)
        release_first.set()
        first.result(timeout=2)
        second.result(timeout=2)

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert set(persisted) == {"alpha", "beta"}
    assert "memory-mcp" not in persisted


def test_custom_config_reader_and_writer_require_object_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("CUSTOM_MCPS_DIR", str(tmp_path))
    root = tmp_path / "demo"
    root.mkdir()
    path = root / "mcp.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(Exception):
        load_custom_config("demo")

    with pytest.raises(TypeError):
        save_custom_config("demo", ["not", "an", "object"])

    save_custom_config("demo", {"enabled": False})
    assert load_custom_config("demo") == {"enabled": False}
