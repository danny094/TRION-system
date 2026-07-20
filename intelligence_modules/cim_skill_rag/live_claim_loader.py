"""Loader for live-claim token sets from live_claim_tokens.csv.

Rule source: intelligence_modules/cim_skill_rag/live_claim_tokens.csv
Schema: token, claim_kind, language

Hot-reload: file is re-parsed whenever its mtime changes (canonical pattern
from core/classifier/patterns.py — module-level _cache dict, no lru_cache).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

_CSV_PATH = Path(__file__).resolve().parent / "live_claim_tokens.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_live_claim_tokens() -> Dict[str, Tuple[str, ...]]:
    """Return token groups keyed by claim_kind.

    Returns an empty dict if the CSV file is missing.
    Consumers should treat missing groups as empty tuples via .get(kind, ()).
    Re-parses the CSV whenever its mtime changes (hot-reload).
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]
    groups: Dict[str, list] = {}
    with _CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            token = str(row.get("token") or "").strip()
            kind = str(row.get("claim_kind") or "").strip().lower()
            if token and kind:
                groups.setdefault(kind, []).append(token)
    result: Dict[str, Tuple[str, ...]] = {kind: tuple(tokens) for kind, tokens in groups.items()}
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
