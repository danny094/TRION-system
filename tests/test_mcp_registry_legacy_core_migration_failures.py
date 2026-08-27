import hashlib
import json
from pathlib import Path

import pytest

import mcp.installer_common as installer_common
import mcp.installer_registry as registry_writer


def _bind_bytes(monkeypatch, tmp_path, raw):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    path.write_bytes(raw)
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    return path


def _bind_payload(monkeypatch, tmp_path, payload):
    return _bind_bytes(monkeypatch, tmp_path, json.dumps(payload).encode("utf-8"))


def _set_core_ids(monkeypatch, core_ids):
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: set(core_ids))


def test_initial_custom_only_apply_is_a_side_effect_free_noop(monkeypatch, tmp_path):
    raw = b'{"alpha":{"enabled":true},"beta":{"enabled":false}}\n'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})

    result = registry_writer.migrate_legacy_core_entries(apply=True)

    assert result["status"] == "nothing_to_migrate"
    assert result["backup_path"] is None
    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


def test_multi_core_apply_preserves_all_custom_entries(monkeypatch, tmp_path):
    core_ids = {"memory-mcp", "time-mcp", "container-commander"}
    custom = {"alpha": {"nested": [1, 2]}, "beta": {"enabled": False}}
    path = _bind_payload(
        monkeypatch,
        tmp_path,
        {**{name: {"legacy": True} for name in core_ids}, **custom},
    )
    _set_core_ids(monkeypatch, core_ids)

    result = registry_writer.migrate_legacy_core_entries(apply=True)

    assert result["detected_core_ids"] == sorted(core_ids)
    assert json.loads(path.read_bytes()) == custom


def test_all_core_entries_produce_a_valid_empty_custom_registry(monkeypatch, tmp_path):
    from mcp.desired_state import MCPRegistrySourceStatus, load_registry_source

    core_ids = {"memory-mcp", "time-mcp", "container-commander"}
    path = _bind_payload(monkeypatch, tmp_path, {name: {} for name in core_ids})
    _set_core_ids(monkeypatch, core_ids)

    registry_writer.migrate_legacy_core_entries(apply=True)

    assert json.loads(path.read_bytes()) == {}
    assert load_registry_source(path, core_ids=core_ids).status is MCPRegistrySourceStatus.VALID


def test_backup_failure_leaves_registry_byte_identical(monkeypatch, tmp_path):
    raw = b'{"memory-mcp":{"enabled":true}}\n'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})

    real_replace = installer_common.os.replace

    def fail_backup(source, target):
        if Path(target) != path:
            raise OSError("backup failed")
        real_replace(source, target)

    monkeypatch.setattr(installer_common.os, "replace", fail_backup)

    with pytest.raises(OSError, match="backup failed"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


def test_registry_replace_failure_preserves_original_and_backup(monkeypatch, tmp_path):
    raw = b'{"memory-mcp":{"enabled":true}}\n'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})
    real_replace = installer_common.os.replace

    def fail_registry_replace(source, target):
        if Path(target) == path:
            raise OSError("registry replace failed")
        real_replace(source, target)

    monkeypatch.setattr(installer_common.os, "replace", fail_registry_replace)

    with pytest.raises(OSError, match="registry replace failed"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    backups = [item for item in tmp_path.iterdir() if item != path]
    assert path.read_bytes() == raw
    assert len(backups) == 1
    assert backups[0].read_bytes() == raw


def test_backup_and_full_sha256_use_exact_original_bytes(monkeypatch, tmp_path):
    raw = b'{\r\n  "memory-mcp": {"enabled": true}\r\n}\r\n'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})

    result = registry_writer.migrate_legacy_core_entries(apply=True)

    digest = hashlib.sha256(raw).hexdigest()
    backup = Path(result["backup_path"])
    assert len(digest) == 64
    assert backup.name == f"mcp_registry.json.pre-core-migration-{digest}.json"
    assert backup.read_bytes() == raw


def test_duplicate_json_keys_fail_closed_without_backup(monkeypatch, tmp_path):
    raw = b'{"memory-mcp":{},"custom":{"v":1},"custom":{"v":2}}'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})

    with pytest.raises(ValueError, match="duplicate JSON key"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


def test_nested_duplicate_json_keys_fail_closed_only_for_migration(monkeypatch, tmp_path):
    from mcp.desired_state import MCPRegistrySourceStatus, load_registry_source

    raw = b'{"memory-mcp":{},"custom":{"nested":{"v":1,"v":2}}}'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})

    with pytest.raises(ValueError, match="duplicate JSON key"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    reader = load_registry_source(path, core_ids=frozenset())
    assert reader.status is MCPRegistrySourceStatus.VALID
    assert reader.custom_registry["custom"]["nested"]["v"] == 2


def test_invalid_utf8_fails_closed_without_backup(monkeypatch, tmp_path):
    raw = b'{"memory-mcp":{"label":"\xff"}}'
    path = _bind_bytes(monkeypatch, tmp_path, raw)
    _set_core_ids(monkeypatch, {"memory-mcp"})

    with pytest.raises(ValueError, match="blocks legacy-core migration"):
        registry_writer.migrate_legacy_core_entries(apply=True)

    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]
