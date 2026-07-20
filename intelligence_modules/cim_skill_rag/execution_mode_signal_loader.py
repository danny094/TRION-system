"""Loader for execution-mode signal phrases from execution_mode_signals_v2.csv.

Rule source: intelligence_modules/cim_skill_rag/execution_mode_signals_v2.csv
Schema: signal_phrase, language, mode, confidence, category, example_context

Modes: "persistent" (recurring/scheduled tasks), "one_shot" (single execution),
"loop_marker" (short repetition markers like "5x", "mehrfach").

Consumer: core/routing_frame/builder/intent.py:detect_loop_signals reads
loop_marker- and persistent-phrases — all loop/repetition detection comes
from this CSV; no hardcoded LOOP_MARKERS constant in Core.
(D1-Vollfix, 2026-06-12)

Hot-reload: file is re-parsed whenever its mtime changes (canonical pattern
from core/classifier/patterns.py — module-level _cache dict, no lru_cache).

(PIANO 1.0 D1-Fix, 2026-06-11; D1-Vollfix, 2026-06-12)
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

_CSV_PATH = Path(__file__).resolve().parent / "execution_mode_signals_v2.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_execution_mode_signals() -> Dict[str, Tuple[str, ...]]:
    """Return signal-phrase groups keyed by mode.

    Returns a dict mapping mode → (phrase1, phrase2, ...).
    Returns an empty dict if the CSV file is missing.
    Re-parses the CSV whenever its mtime changes (hot-reload).

    Known modes: "persistent", "one_shot".
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]
    groups: Dict[str, list] = {}
    with _CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            phrase = str(row.get("signal_phrase") or "").strip().lower()
            mode = str(row.get("mode") or "").strip().lower()
            if phrase and mode:
                groups.setdefault(mode, []).append(phrase)
    result: Dict[str, Tuple[str, ...]] = {
        mode: tuple(phrases) for mode, phrases in groups.items()
    }
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
