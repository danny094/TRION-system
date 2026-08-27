import json
import multiprocessing
from pathlib import Path

import mcp.installer_registry as registry_writer


def _bind_registry_path(path):
    import mcp.config as mcp_config

    mcp_config._CONFIG_PATH = Path(path)


def _hold_upsert_before_replace(path, ready, release):
    _bind_registry_path(path)
    real_write = registry_writer._write_registry

    def held_write(registry):
        ready.send("upsert_read_complete")
        release.recv()
        real_write(registry)

    registry_writer._write_registry = held_write
    registry_writer.upsert_registry_entry("alpha", {"enabled": True})


def _hold_migration_before_replace(path, ready, release):
    import mcp.installer_common as installer_common

    _bind_registry_path(path)
    real_write = installer_common.atomic_write_bytes

    def held_write(target, content):
        if Path(target) == Path(path):
            ready.send("migration_before_replace")
            release.recv()
        real_write(target, content)

    installer_common.atomic_write_bytes = held_write
    registry_writer.migrate_legacy_core_entries(apply=True)


def _try_nonblocking_upsert(path, result):
    _bind_registry_path(path)
    real_flock = registry_writer.fcntl.flock

    def nonblocking_flock(fd, operation):
        if operation == registry_writer.fcntl.LOCK_EX:
            operation |= registry_writer.fcntl.LOCK_NB
        return real_flock(fd, operation)

    registry_writer.fcntl.flock = nonblocking_flock
    try:
        registry_writer.upsert_registry_entry("beta", {"enabled": True})
    except BlockingIOError:
        result.send("blocked")
    else:
        result.send("acquired")


def _start_holder(context, target, path):
    ready_parent, ready_child = context.Pipe()
    release_parent, release_child = context.Pipe()
    process = context.Process(target=target, args=(str(path), ready_child, release_child))
    process.start()
    assert ready_parent.poll(5)
    ready_parent.recv()
    return process, release_parent


def _assert_upsert_is_blocked(context, path):
    result_parent, result_child = context.Pipe()
    process = context.Process(target=_try_nonblocking_upsert, args=(str(path), result_child))
    process.start()
    assert result_parent.poll(5)
    assert result_parent.recv() == "blocked"
    process.join(5)
    assert process.exitcode == 0


def test_upsert_blocks_second_process_across_read_to_replace(monkeypatch, tmp_path):
    context = multiprocessing.get_context("spawn")
    path = tmp_path / "mcp_registry.json"
    path.write_text("{}", encoding="utf-8")
    process, release = _start_holder(context, _hold_upsert_before_replace, path)

    _assert_upsert_is_blocked(context, path)
    release.send("continue")
    process.join(5)
    assert process.exitcode == 0

    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    registry_writer.upsert_registry_entry("beta", {"enabled": True})
    assert set(json.loads(path.read_text(encoding="utf-8"))) == {"alpha", "beta"}


def test_migration_blocks_upsert_process_until_replace_finishes(monkeypatch, tmp_path):
    context = multiprocessing.get_context("spawn")
    path = tmp_path / "mcp_registry.json"
    path.write_text('{"memory-mcp":{},"custom":{}}', encoding="utf-8")
    process, release = _start_holder(context, _hold_migration_before_replace, path)

    _assert_upsert_is_blocked(context, path)
    release.send("continue")
    process.join(5)
    assert process.exitcode == 0

    import mcp.config as mcp_config

    monkeypatch.setattr(mcp_config, "_CONFIG_PATH", path)
    registry_writer.upsert_registry_entry("beta", {"enabled": True})
    assert set(json.loads(path.read_text(encoding="utf-8"))) == {"custom", "beta"}
