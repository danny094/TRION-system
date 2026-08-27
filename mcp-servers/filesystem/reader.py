from __future__ import annotations

import os
import stat
from pathlib import Path

from .contracts import READ_DEFAULT_BYTES, READ_MAX_BYTES, FilesystemFailure, bounded_value
from .path_policy import open_target


def read_text(root: Path, relative_path: str, max_bytes: int | None = None) -> dict[str, object]:
    byte_limit = bounded_value(max_bytes, default=READ_DEFAULT_BYTES, hard_cap=READ_MAX_BYTES, field="max_bytes")
    with open_target(root, relative_path) as target:
        if not stat.S_ISREG(target.stat_result.st_mode):
            raise FilesystemFailure("NOT_A_FILE", "read target must be a regular file")
        size_bytes = target.stat_result.st_size
        if size_bytes > byte_limit:
            raise FilesystemFailure("SIZE_LIMIT", f"file exceeds max_bytes {byte_limit}")
        chunks = []
        remaining = size_bytes
        while remaining:
            chunk = os.read(target.fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        final_stat = os.fstat(target.fd)
    raw = b"".join(chunks)
    if len(raw) != size_bytes:
        raise FilesystemFailure("READ_FAILED", "file changed or ended before the bounded read completed")
    if (final_stat.st_size, final_stat.st_mtime_ns) != (size_bytes, target.stat_result.st_mtime_ns):
        raise FilesystemFailure("READ_FAILED", "file changed during the bounded read")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FilesystemFailure("UNSUPPORTED_ENCODING", "file is not valid UTF-8 text") from exc
    return {
        "relative_path": target.relative_path,
        "text": text,
        "size_bytes": size_bytes,
        "read_bytes": len(raw),
        "complete": True,
        "truncated": False,
    }
