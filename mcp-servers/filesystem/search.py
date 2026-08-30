from __future__ import annotations

from pathlib import Path

from .contracts import (
    SEARCH_DEFAULT_DEPTH,
    SEARCH_DEFAULT_RESULTS,
    SEARCH_MAX_DEPTH,
    SEARCH_MAX_RESULTS,
    FilesystemFailure,
    bounded_value,
)
from .listing import walk_entries
from .path_policy import normalize_relative_path


def search_paths(
    root: Path,
    query: str,
    relative_path: str | None = None,
    max_results: int | None = None,
    max_depth: int | None = None,
) -> dict[str, object]:
    if not isinstance(query, str):
        raise FilesystemFailure("MALFORMED_REQUEST", "query must be a string")
    clean_query = query.strip()
    if not clean_query:
        raise FilesystemFailure("MALFORMED_REQUEST", "query is required")
    result_cap = bounded_value(max_results, default=SEARCH_DEFAULT_RESULTS, hard_cap=SEARCH_MAX_RESULTS, field="max_results")
    depth_cap = bounded_value(max_depth, default=SEARCH_DEFAULT_DEPTH, hard_cap=SEARCH_MAX_DEPTH, field="max_depth")
    base = normalize_relative_path(relative_path, allow_root=True)
    entries, depth_limited, scan_limited = walk_entries(
        root,
        base,
        depth_cap,
        SEARCH_MAX_RESULTS + 1,
    )
    folded = clean_query.casefold()
    matches = [entry for entry in entries if folded in str(entry["relative_path"]).casefold()]
    truncated = len(matches) > result_cap
    return {
        "query": clean_query,
        "matches": matches[:result_cap],
        "complete": not truncated and not depth_limited and not scan_limited,
        "truncated": truncated,
    }
