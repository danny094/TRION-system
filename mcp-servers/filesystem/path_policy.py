from __future__ import annotations

import errno
import os
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from .contracts import FilesystemFailure


@dataclass(frozen=True)
class OpenTarget:
    fd: int
    relative_path: str
    stat_result: os.stat_result


def normalize_relative_path(value: str | None, *, allow_root: bool = False) -> str:
    if value is not None and not isinstance(value, str):
        raise FilesystemFailure("MALFORMED_REQUEST", "relative_path must be a string")
    raw = "" if value is None else value
    if "\x00" in raw:
        raise FilesystemFailure("MALFORMED_REQUEST", "relative_path contains a NUL byte")
    candidate = PurePosixPath(raw)
    if candidate.is_absolute():
        raise FilesystemFailure("ABSOLUTE_PATH_FORBIDDEN", "relative_path must not be absolute")
    parts = candidate.parts
    if any(part in {"", ".", ".."} for part in parts):
        if allow_root and raw in {"", "."}:
            return ""
        raise FilesystemFailure("OUTSIDE_ROOT", "relative_path must stay below the configured root")
    if not parts:
        if allow_root:
            return ""
        raise FilesystemFailure("MALFORMED_REQUEST", "relative_path is required")
    return "/".join(parts)


@contextmanager
def open_target(root: Path, relative_path: str | None, *, allow_root: bool = False) -> Iterator[OpenTarget]:
    normalized = normalize_relative_path(relative_path, allow_root=allow_root)
    root_fd = _open_root(root)
    current_fd = root_fd
    components = normalized.split("/") if normalized else ()
    try:
        for index, component in enumerate(components):
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
            if index < len(components) - 1:
                flags |= os.O_DIRECTORY
            else:
                flags |= os.O_NONBLOCK
            next_fd = _open_component(component, flags, current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        result = os.fstat(current_fd)
        yield OpenTarget(current_fd, normalized, result)
    finally:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


def entry_from_target(target: OpenTarget) -> dict[str, object]:
    mode = target.stat_result.st_mode
    if stat.S_ISDIR(mode):
        entry_type = "directory"
        size_bytes = None
    elif stat.S_ISREG(mode):
        entry_type = "file"
        size_bytes = target.stat_result.st_size
    else:
        raise FilesystemFailure("NOT_A_FILE", "target is not a regular file or directory")
    return {"relative_path": target.relative_path, "entry_type": entry_type, "size_bytes": size_bytes}


def _open_root(root: Path) -> int:
    try:
        return os.open(root, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise _failure_for_oserror(exc, "configured root") from exc


def _open_component(component: str, flags: int, parent_fd: int) -> int:
    try:
        return os.open(component, flags, dir_fd=parent_fd)
    except OSError as exc:
        if _is_symlink(component, parent_fd):
            raise FilesystemFailure("SYMLINK_ESCAPE", f"symlinks are forbidden: {component}") from exc
        raise _failure_for_oserror(exc, component) from exc


def _is_symlink(component: str, parent_fd: int) -> bool:
    try:
        result = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISLNK(result.st_mode)


def _failure_for_oserror(exc: OSError, target: str) -> FilesystemFailure:
    if exc.errno in {errno.ELOOP, errno.EMLINK}:
        return FilesystemFailure("SYMLINK_ESCAPE", f"symlinks are forbidden: {target}")
    if exc.errno == errno.ENOENT:
        return FilesystemFailure("NOT_FOUND", f"target not found: {target}")
    if exc.errno == errno.ENOTDIR:
        return FilesystemFailure("NOT_FOUND", f"target component is not a directory: {target}")
    return FilesystemFailure("OUTSIDE_ROOT", f"target cannot be opened safely: {target}")
