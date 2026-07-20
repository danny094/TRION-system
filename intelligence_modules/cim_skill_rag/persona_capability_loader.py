"""Loader for persona capability-detection rules from persona_capability_rules.csv.

Rule source: intelligence_modules/cim_skill_rag/persona_capability_rules.csv
Schema: capability_flag, match_type, value

match_type values:
  domain_eq          — tool_intent.domain equals value (case-insensitive)
  name_prefix        — tool name starts with value (case-insensitive)
  name_contains      — value is a substring of tool name (case-insensitive)
  description_contains — value is a substring of tool description (case-insensitive)

Hot-reload: file is re-parsed whenever its mtime changes (canonical pattern
from core/classifier/patterns.py — module-level _cache dict, no lru_cache).

(PIANO 1.0 Schritt 3.2, 2026-06-11)
"""

from __future__ import annotations

import csv
from pathlib import Path

_CSV_PATH = Path(__file__).resolve().parent / "persona_capability_rules.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_persona_capability_rules() -> dict[str, list[tuple[str, str]]]:
    """Return capability rules grouped by capability_flag.

    Returns a dict mapping flag → [(match_type, value), ...].
    Returns an empty dict if the CSV file is missing.
    Re-parses the CSV whenever its mtime changes (hot-reload).
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]
    groups: dict[str, list[tuple[str, str]]] = {}
    with _CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            flag = str(row.get("capability_flag") or "").strip()
            match_type = str(row.get("match_type") or "").strip()
            value = str(row.get("value") or "").strip()
            if flag and match_type and value:
                groups.setdefault(flag, []).append((match_type, value))
    result: dict[str, list[tuple[str, str]]] = groups
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
