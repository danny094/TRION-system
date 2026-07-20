"""Loader for memory-graph-search blocking signals from memory_block_signals.csv.

Rule source: intelligence_modules/cim_skill_rag/memory_block_signals.csv
Schema: signal_phrase, signal_type, language

signal_type values:
  analysis_block    — triggers when user asks for analysis/statistics over memory
                      (formerly MEMORY_ANALYSIS_KW in core/thinking/fallback/memory_signal.py)
  vague_search_block — triggers when user describes a vague/arbitrary memory search
                      (formerly VAGUE_MEMORY_SEARCH_KW in core/thinking/fallback/memory_signal.py)

Moved to intelligence_modules as part of PIANO 1.0 B3 fix (2026-06-11).

Hot-reload: file is re-parsed whenever its mtime changes (canonical pattern
from core/classifier/patterns.py — module-level _cache dict, no lru_cache).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

_CSV_PATH = Path(__file__).resolve().parent / "memory_block_signals.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_memory_block_signals() -> Dict[str, Tuple[str, ...]]:
    """Return signal groups keyed by signal_type.

    Returns a dict mapping signal_type → (phrase1, phrase2, ...).
    Returns an empty dict if the CSV file is missing.
    Re-parses the CSV whenever its mtime changes (hot-reload).

    Known signal_types: "analysis_block", "vague_search_block".
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]
    groups: Dict[str, list] = {}
    with _CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            phrase = str(row.get("signal_phrase") or "").strip()
            signal_type = str(row.get("signal_type") or "").strip().lower()
            if phrase and signal_type:
                groups.setdefault(signal_type, []).append(phrase)
    result: Dict[str, Tuple[str, ...]] = {
        sig: tuple(phrases) for sig, phrases in groups.items()
    }
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
