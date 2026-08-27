from pathlib import Path

import pytest

import mcp.installer_common as installer_common
import mcp.installer_registry as registry_writer


def _bind_registry(monkeypatch, tmp_path, raw):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    path.write_bytes(raw)
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: {"memory-mcp"})
    return path


def test_stale_registry_before_backup_preserves_external_write(monkeypatch, tmp_path):
    state_a = b'{"memory-mcp":{},"alpha":{}}\n'
    state_b = b'{"memory-mcp":{},"alpha":{},"external":{}}\n'
    path = _bind_registry(monkeypatch, tmp_path, state_a)
    real_read_bytes = Path.read_bytes
    first_registry_read = True

    def read_then_race(target):
        nonlocal first_registry_read
        value = real_read_bytes(target)
        if target == path and first_registry_read:
            first_registry_read = False
            path.write_bytes(state_b)
        return value

    monkeypatch.setattr(Path, "read_bytes", read_then_race)

    with pytest.raises(ValueError, match="stale registry state"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    assert real_read_bytes(path) == state_b
    assert list(tmp_path.iterdir()) == [path]


def test_stale_registry_after_backup_preserves_external_write(monkeypatch, tmp_path):
    state_a = b'{"memory-mcp":{},"alpha":{}}\n'
    state_b = b'{"memory-mcp":{},"alpha":{},"external":{}}\n'
    path = _bind_registry(monkeypatch, tmp_path, state_a)
    real_atomic_write_bytes = installer_common.atomic_write_bytes
    external_write_done = False

    def backup_then_race(target, content):
        nonlocal external_write_done
        real_atomic_write_bytes(target, content)
        if Path(target) != path and not external_write_done:
            path.write_bytes(state_b)
            external_write_done = True

    monkeypatch.setattr(installer_common, "atomic_write_bytes", backup_then_race)

    with pytest.raises(ValueError, match="stale registry state"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    backups = [item for item in tmp_path.iterdir() if item != path]
    assert path.read_bytes() == state_b
    assert len(backups) == 1
    assert backups[0].read_bytes() == state_a
