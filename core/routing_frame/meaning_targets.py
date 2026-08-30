"""Build typed TMR target candidates without operation or scope decisions."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from core.routing_frame.meaning_signals import collect_matches, dedupe_preserve_order
from intelligence_modules.cim_skill_rag.meaning_target_pattern_loader import (
    load_meaning_target_patterns,
)


TargetMatch = Tuple[str, str]


def target_candidates_from_text(
    text: str,
    role_rows: List[Dict[str, str]],
) -> Tuple[Tuple[str, ...], Tuple[TargetMatch, ...], str]:
    """Return known aliases plus guarded root-relative syntax matches."""
    lowered = text.lower()
    alias_matches = collect_matches(
        lowered,
        [row for row in role_rows if row.get("role") == "target_alias"],
        "value",
    )
    pattern_matches = _pattern_matches(text)
    target_matches = [*pattern_matches, *alias_matches]
    return (
        dedupe_preserve_order([value for value, _ in target_matches]),
        tuple(target_matches),
        "rule:meaning_target_patterns" if pattern_matches else "rule:meaning_role_tokens",
    )


def _pattern_matches(text: str) -> List[TargetMatch]:
    positioned: List[Tuple[int, int, str, str]] = []
    for row_index, row in enumerate(load_meaning_target_patterns()):
        for match in re.finditer(row["pattern"], text, re.IGNORECASE):
            target = str(match.group("target") or "").strip()
            if _is_safe_relative_target(target):
                positioned.append((match.start("target"), row_index, target, target))
    positioned.sort(key=lambda item: (item[0], item[1]))
    return [(target, span) for _position, _row, target, span in positioned]


def _is_safe_relative_target(target: str) -> bool:
    if not target or "\x00" in target or target.startswith(("/", ".")):
        return False
    return all(part not in {"", ".", ".."} for part in target.split("/"))
