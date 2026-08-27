import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import mcp.installer_common as installer_common
import mcp.installer_registry as registry_writer


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "migrate_mcp_registry_core_entries.py"


def _bind_registry(monkeypatch, tmp_path, payload):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    raw = json.dumps(payload, indent=2) + "\n"
    path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    return path, raw


def _migrate(*, apply=False):
    return registry_writer.migrate_legacy_core_entries(apply=apply)


@pytest.mark.parametrize(
    "core_ids",
    [
        {"memory-mcp"},
        {"memory-mcp", "time-mcp", "container-commander"},
    ],
)
def test_dry_run_detects_all_current_core_collisions(monkeypatch, tmp_path, core_ids):
    path, raw = _bind_registry(
        monkeypatch,
        tmp_path,
        {name: {"enabled": True} for name in sorted(core_ids)},
    )
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: set(core_ids))

    result = _migrate()

    assert result == {
        "status": "dry_run",
        "mode": "dry_run",
        "registry_path": str(path),
        "detected_core_ids": sorted(core_ids),
        "backup_path": None,
    }
    assert path.read_text(encoding="utf-8") == raw
    assert list(tmp_path.iterdir()) == [path]


def test_apply_removes_only_current_core_ids_and_preserves_custom_entries(
    monkeypatch, tmp_path
):
    payload = {
        "memory-mcp": {"enabled": False, "legacy": {"source": "old"}},
        "time-mcp": {"enabled": True, "custom": "preserve"},
        "container-commander": {"enabled": True, "custom": "preserve"},
        "alpha-custom": {"enabled": True, "nested": {"items": [1, 2]}},
        "beta-custom": {"enabled": False},
    }
    path, raw = _bind_registry(monkeypatch, tmp_path, payload)
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: {"memory-mcp"})

    result = _migrate(apply=True)

    assert result["status"] == "applied"
    assert result["mode"] == "apply"
    assert result["registry_path"] == str(path)
    assert result["detected_core_ids"] == ["memory-mcp"]
    backup_path = Path(result["backup_path"])
    assert backup_path.read_text(encoding="utf-8") == raw
    assert json.loads(path.read_text(encoding="utf-8")) == {
        name: config for name, config in payload.items() if name != "memory-mcp"
    }


def test_apply_uses_atomic_writer_for_backup_before_registry(monkeypatch, tmp_path):
    path, _ = _bind_registry(monkeypatch, tmp_path, {"memory-mcp": {"enabled": True}})
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: {"memory-mcp"})
    real_atomic_write = installer_common.atomic_write_bytes
    written_paths = []

    def tracked_atomic_write(target, content):
        written_paths.append(target)
        real_atomic_write(target, content)

    monkeypatch.setattr(installer_common, "atomic_write_bytes", tracked_atomic_write)

    result = _migrate(apply=True)

    assert written_paths == [Path(result["backup_path"]), path]


def test_second_apply_is_idempotent_and_creates_no_second_backup(monkeypatch, tmp_path):
    path, _ = _bind_registry(monkeypatch, tmp_path, {"memory-mcp": {"enabled": True}})
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: {"memory-mcp"})
    first = _migrate(apply=True)
    files_after_first = sorted(tmp_path.iterdir())
    registry_after_first = path.read_bytes()

    second = _migrate(apply=True)

    assert first["status"] == "applied"
    assert second == {
        "status": "nothing_to_migrate",
        "mode": "apply",
        "registry_path": str(path),
        "detected_core_ids": [],
        "backup_path": None,
    }
    assert sorted(tmp_path.iterdir()) == files_after_first
    assert path.read_bytes() == registry_after_first


def test_apply_requires_a_boolean_and_never_accepts_truthy_text(monkeypatch, tmp_path):
    path, raw = _bind_registry(monkeypatch, tmp_path, {"memory-mcp": {"enabled": True}})
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: {"memory-mcp"})

    with pytest.raises(TypeError, match="apply must be a bool"):
        registry_writer.migrate_legacy_core_entries(apply="yes")

    assert path.read_text(encoding="utf-8") == raw
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("raw", ["{broken-json", "[]", '{"demo": []}'])
def test_invalid_registry_fails_closed_without_mutation(monkeypatch, tmp_path, raw):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    monkeypatch.setattr(registry_writer, "core_mcp_names", lambda: {"memory-mcp"})

    with pytest.raises(ValueError, match="blocks legacy-core migration"):
        _migrate(apply=True)

    assert path.read_text(encoding="utf-8") == raw
    assert list(tmp_path.iterdir()) == [path]


def test_operator_cli_defaults_to_dry_run_and_requires_apply(monkeypatch, tmp_path):
    path, raw = _bind_registry(monkeypatch, tmp_path, {"memory-mcp": {"enabled": True}})
    env = {**os.environ, "MCP_REGISTRY_PATH": str(path)}

    dry_run = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert dry_run.returncode == 0
    assert json.loads(dry_run.stdout)["status"] == "dry_run"
    assert path.read_text(encoding="utf-8") == raw

    applied = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert applied.returncode == 0
    report = json.loads(applied.stdout)
    assert report["status"] == "applied"
    assert report["mode"] == "apply"
    assert report["registry_path"] == str(path)
    assert report["detected_core_ids"] == ["memory-mcp"]
    assert Path(report["backup_path"]).exists()


def test_operator_cli_reports_invalid_registry_with_exit_two(monkeypatch, tmp_path):
    import mcp.config as mcp_config

    path = tmp_path / "mcp_registry.json"
    path.write_text("{broken-json", encoding="utf-8")
    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    env = {**os.environ, "MCP_REGISTRY_PATH": str(path)}

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply"], cwd=ROOT, env=env,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "error"
    assert path.read_text(encoding="utf-8") == "{broken-json"
    assert list(tmp_path.iterdir()) == [path]
