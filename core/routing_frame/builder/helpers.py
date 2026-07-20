"""Small parsing and counting helpers for the routing frame builder.

`count_items` counts valid dict entries in an iterable (used for
available/selected tool counts).  `repeat_count` extracts the explicit
repetition number (2x–5x) from the lowercased user text.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable


def count_items(items: Iterable[Dict[str, Any]] | None) -> int:
    if items is None:
        return 0
    return sum(1 for item in items if isinstance(item, dict))


def repeat_count(lowered: str) -> int:
    for count in (5, 4, 3, 2):
        if f"{count}x" in lowered:
            return count
    return 1
