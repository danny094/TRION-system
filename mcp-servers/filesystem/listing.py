from __future__ import annotations

import os
import stat
from pathlib import Path

from .contracts import (
    LIST_DEFAULT_DEPTH,
    LIST_DEFAULT_ENTRIES,
    LIST_MAX_DEPTH,
    LIST_MAX_ENTRIES,
    FilesystemFailure,
    bounded_value,
)
from .path_policy import entry_from_target, normalize_relative_path, open_target


def list_entries(
    root: Path,
    relative_path: str | None = None,
    max_entries: int | None = None,
    max_depth: int | None = None,
) -> dict[str, object]:
    entry_cap = bounded_value(max_entries, default=LIST_DEFAULT_ENTRIES, hard_cap=LIST_MAX_ENTRIES, field="max_entries")
    depth_cap = bounded_value(max_depth, default=LIST_DEFAULT_DEPTH, hard_cap=LIST_MAX_DEPTH, field="max_depth")
    if relative_path is not None:
        normalized = normalize_relative_path(relative_path)
        try:
            with open_target(root, normalized) as target:
                entry = entry_from_target(target)
        except FilesystemFailure as failure:
            if failure.code != "NOT_FOUND":
                raise
            return {"relative_path": normalized, "exists": False, "entries": [], "complete": True, "truncated": False}
        return {"relative_path": normalized, "exists": True, "entries": [entry], "complete": True, "truncated": False}
    entries, depth_limited, scan_limited = walk_entries(root, "", depth_cap, entry_cap + 1)
    truncated = len(entries) > entry_cap
    return {
        "entries": entries[:entry_cap],
        "complete": not truncated and not depth_limited and not scan_limited,
        "truncated": truncated,
    }


def walk_entries(
    root: Path,
    base: str,
    max_depth: int,
    scan_limit: int,
) -> tuple[list[dict[str, object]], bool, bool]:
    pending = [(base, 0)]
    entries: list[dict[str, object]] = []
    depth_limited = False
    scan_limited = False
    scanned = 0
    while pending and scanned < scan_limit:
        current, depth = pending.pop()
        with open_target(root, current, allow_root=True) as directory:
            if not stat.S_ISDIR(directory.stat_result.st_mode):
                raise FilesystemFailure("NOT_A_FILE", "list target must be a directory")
            names, names_limited = _bounded_names(directory.fd, scan_limit - scanned)
            scan_limited = scan_limited or names_limited
        child_directories = []
        for name in names:
            scanned += 1
            child = f"{current}/{name}" if current else name
            try:
                with open_target(root, child) as target:
                    entry = entry_from_target(target)
            except FilesystemFailure as failure:
                if failure.code == "SYMLINK_ESCAPE":
                    continue
                raise
            entries.append(entry)
            if entry["entry_type"] == "directory":
                if depth + 1 < max_depth:
                    child_directories.append((child, depth + 1))
                else:
                    depth_limited = True
        pending.extend(reversed(child_directories))
    scan_limited = scan_limited or bool(pending)
    return sorted(entries, key=lambda item: str(item["relative_path"])), depth_limited, scan_limited


def _bounded_names(directory_fd: int, limit: int) -> tuple[list[str], bool]:
    names = []
    with os.scandir(directory_fd) as iterator:
        for entry in iterator:
            if len(names) >= limit:
                return sorted(names), True
            names.append(entry.name)
    return sorted(names), False
