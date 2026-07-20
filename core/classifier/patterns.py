"""CSV-backed policy pattern matcher for the classifier.

Patterns and their metadata live in
``intelligence_modules/cim_policy/cim_policy.csv``. The file is parsed lazily
and re-loaded when its mtime changes (hot-reload).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

POLICY_CSV = (
    Path(__file__).resolve().parents[2]
    / "intelligence_modules"
    / "cim_policy"
    / "cim_policy.csv"
)
PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}


@dataclass(frozen=True)
class PatternMatch:
    pattern_id: str
    trigger_category: str
    safety_level: str
    requires_confirmation: bool
    confidence: float
    action_if_missing: str
    action_if_present: str


_cache: Dict[str, object] = {"mtime": None, "rows": []}


def match(user_text: str) -> Optional[PatternMatch]:
    text = (user_text or "").strip().lower()
    if not text:
        return None
    for row in _load_rows():
        pattern: re.Pattern = row["_pattern"]  # type: ignore[assignment]
        m = pattern.search(text)
        if not m:
            continue
        coverage = _coverage(len(m.group()), len(text))
        min_conf = _float(row.get("intent_confidence"), 0.5)
        confirm_gated = _bool(row.get("requires_confirmation"))
        if not confirm_gated and coverage < min_conf * 0.8:
            continue
        return PatternMatch(
            pattern_id=str(row.get("pattern_id") or ""),
            trigger_category=str(row.get("trigger_category") or ""),
            safety_level=str(row.get("safety_level") or "low"),
            requires_confirmation=confirm_gated,
            confidence=max(coverage, min_conf if confirm_gated else 0.0),
            action_if_missing=str(row.get("action_if_missing") or ""),
            action_if_present=str(row.get("action_if_present") or ""),
        )
    return None


def _load_rows() -> List[Dict[str, object]]:
    if not POLICY_CSV.is_file():
        return []
    mtime = POLICY_CSV.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["rows"]  # type: ignore[return-value]
    rows: List[Dict[str, object]] = []
    with POLICY_CSV.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            regex_str = (row.get("trigger_regex") or "").strip()
            if not regex_str:
                continue
            try:
                row["_pattern"] = re.compile(regex_str, re.IGNORECASE | re.UNICODE)
            except re.error:
                continue
            rows.append(row)
    rows.sort(key=lambda r: PRIORITY_ORDER.get(str(r.get("priority") or "normal"), 2))
    _cache["mtime"] = mtime
    _cache["rows"] = rows
    return rows


def _coverage(match_len: int, text_len: int) -> float:
    return min(1.0, match_len / max(text_len * 0.3, 1.0))


def _float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _bool(value: object) -> bool:
    return str(value or "").strip().lower() == "true"
