"""Loader for fallback tool-selection rules from tool_selection_rules.csv.

Rule source: intelligence_modules/cim_skill_rag/tool_selection_rules.csv
Schema: signal_phrase, tool_name, language, priority

Priority is ascending (lower value = higher priority). When multiple rules
share the same tool_name, they are grouped together under that tool's priority
level. The consumer iterates groups in priority order and returns the first
tool whose signal phrases contain a substring match in the user text.

The "remember" phrase intentionally appears for both memory_save (priority 20)
and memory_graph_search (priority 30), preserving the pre-PIANO behavior where
memory_save wins when both could match.

Hot-reload: file is re-parsed whenever its mtime changes (canonical pattern
from core/classifier/patterns.py — module-level _cache dict, no lru_cache).
"""

from __future__ import annotations

import csv
from pathlib import Path

_CSV_PATH = Path(__file__).resolve().parent / "tool_selection_rules.csv"

_cache: dict[str, object] = {"mtime": None, "data": []}


def load_tool_selection_rules() -> list[tuple[str, tuple[str, ...]]]:
    """Return tool-selection rules sorted by priority (ascending).

    Returns a list of (tool_name, signal_phrases) tuples. Each tool appears
    at most once; all phrases for the same tool are grouped together.
    Returns an empty list if the CSV file is missing.
    Re-parses the CSV whenever its mtime changes (hot-reload).
    """
    if not _CSV_PATH.exists():
        return []
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]

    groups: dict[tuple[int, str], list[str]] = {}
    with _CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            phrase = str(row.get("signal_phrase") or "").strip()
            tool = str(row.get("tool_name") or "").strip()
            try:
                priority = int(str(row.get("priority") or "99").strip())
            except ValueError:
                priority = 99
            if phrase and tool:
                groups.setdefault((priority, tool), []).append(phrase)

    sorted_groups = sorted(groups.items(), key=lambda kv: kv[0])
    result: list[tuple[str, tuple[str, ...]]] = [
        (tool, tuple(phrases)) for (_, tool), phrases in sorted_groups
    ]
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
