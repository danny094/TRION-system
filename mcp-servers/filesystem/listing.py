from __future__ import annotations

import os
import stat
from heapq import heapify, heappop, heappush
from itertools import islice
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
    with open_target(root, base, allow_root=True) as directory:
        if not stat.S_ISDIR(directory.stat_result.st_mode):
            raise FilesystemFailure("NOT_A_FILE", "list target must be a directory")
        names, scan_limited = _bounded_names(directory.fd, scan_limit)
    pending = [
        (f"{base}/{name}" if base else name, 0)
        for name in names
    ]
    heapify(pending)
    entries: list[dict[str, object]] = []
    depth_limited = False
    scanned = 0
    while pending and scanned < scan_limit:
        current, depth = heappop(pending)
        scanned += 1
        try:
            with open_target(root, current, allow_root=True) as directory:
                entry = entry_from_target(directory)
                entries.append(entry)
                if entry["entry_type"] == "directory":
                    if depth + 1 < max_depth:
                        names, names_limited = _bounded_names(
                            directory.fd, scan_limit - scanned,
                        )
                        scan_limited = scan_limited or names_limited
                        for name in names:
                            heappush(pending, (f"{current}/{name}", depth + 1))
                    else:
                        depth_limited = True
        except FilesystemFailure as failure:
            if failure.code != "SYMLINK_ESCAPE":
                raise
    scan_limited = scan_limited or bool(pending)
    return entries, depth_limited, scan_limited


def _bounded_names(directory_fd: int, limit: int) -> tuple[list[str], bool]:
    with os.scandir(directory_fd) as iterator:
        names = sorted(entry.name for entry in islice(iterator, limit + 1))
    return names[:limit], len(names) > limit
