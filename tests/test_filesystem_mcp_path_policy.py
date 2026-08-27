import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "mcp-servers" / "filesystem"
SERVERS_ROOT = BUNDLE_ROOT.parent


def _module(name: str):
    assert BUNDLE_ROOT.is_dir(), "R6 Filesystem MCP product slice is absent"
    if str(SERVERS_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVERS_ROOT))
    return importlib.import_module(f"filesystem.{name}")


@pytest.mark.parametrize("value", ["/etc/passwd", "../secret", "a/../../secret", "bad\x00name"])
def test_path_policy_blocks_unsafe_relative_paths(tmp_path, value):
    policy = _module("path_policy")

    with pytest.raises(policy.FilesystemFailure) as failure:
        with policy.open_target(tmp_path, value):
            pass
    assert failure.value.code in {
        "ABSOLUTE_PATH_FORBIDDEN",
        "OUTSIDE_ROOT",
        "MALFORMED_REQUEST",
    }


def test_path_policy_blocks_missing_and_symlink_targets(tmp_path):
    policy = _module("path_policy")
    (tmp_path / "real.txt").write_text("safe", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(tmp_path / "real.txt")

    with pytest.raises(policy.FilesystemFailure) as missing:
        with policy.open_target(tmp_path, "missing.txt"):
            pass
    assert missing.value.code == "NOT_FOUND"

    with pytest.raises(policy.FilesystemFailure) as linked:
        with policy.open_target(tmp_path, "link.txt"):
            pass
    assert linked.value.code == "SYMLINK_ESCAPE"


def test_path_policy_classifies_symlink_components_fail_closed(tmp_path):
    policy = _module("path_policy")
    real = tmp_path / "real"
    real.mkdir()
    (real / "status.txt").write_text("safe", encoding="utf-8")
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)

    with pytest.raises(policy.FilesystemFailure) as failure:
        with policy.open_target(tmp_path, "linked/status.txt"):
            pass
    assert failure.value.code == "SYMLINK_ESCAPE"


def test_descriptor_relative_open_blocks_component_swap(tmp_path, monkeypatch):
    policy = _module("path_policy")
    target = tmp_path / "victim.txt"
    outside = tmp_path.parent / "outside-r6.txt"
    target.write_text("safe", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    real_open = policy.os.open
    swapped = False

    def swap_then_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if path == "victim.txt" and dir_fd is not None and not swapped:
            target.unlink()
            target.symlink_to(outside)
            swapped = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(policy.os, "open", swap_then_open)
    with pytest.raises(policy.FilesystemFailure) as failure:
        with policy.open_target(tmp_path, "victim.txt"):
            pass
    assert swapped is True
    assert failure.value.code == "SYMLINK_ESCAPE"


def test_settings_accepts_only_the_product_root(monkeypatch):
    settings = _module("settings")
    monkeypatch.setattr(settings.Path, "is_dir", lambda path: str(path) == "/trion-home")

    assert settings.load_root({}) == Path("/trion-home")
    assert settings.load_root({"TRION_FILESYSTEM_ROOT": "/trion-home"}) == Path("/trion-home")
    for value in (".", "/", "/tmp", "trion-home"):
        with pytest.raises(settings.FilesystemConfigurationError):
            settings.load_root({"TRION_FILESYSTEM_ROOT": value})


@pytest.mark.parametrize("value", [1, True, [], {}])
def test_path_policy_rejects_non_string_relative_paths(tmp_path, value):
    policy = _module("path_policy")

    with pytest.raises(policy.FilesystemFailure) as failure:
        with policy.open_target(tmp_path, value):
            pass
    assert failure.value.code == "MALFORMED_REQUEST"


def test_settings_rejects_missing_product_root(monkeypatch):
    settings = _module("settings")
    monkeypatch.setattr(settings.Path, "is_dir", lambda _path: False)

    with pytest.raises(settings.FilesystemConfigurationError):
        settings.load_root({})


def test_fifo_target_fails_closed_without_blocking(tmp_path):
    fifo = tmp_path / "events.pipe"
    os.mkfifo(fifo)
    script = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            "sys.path.insert(0, str(Path(sys.argv[1]).parent))",
            "from filesystem.contracts import FilesystemFailure",
            "from filesystem.metadata import metadata_for",
            "try:",
            "    metadata_for(Path(sys.argv[2]), 'events.pipe')",
            "except FilesystemFailure as failure:",
            "    print(failure.code)",
            "else:",
            "    raise SystemExit(2)",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", script, str(BUNDLE_ROOT), str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=1,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NOT_A_FILE"
