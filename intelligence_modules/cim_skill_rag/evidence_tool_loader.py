"""Loader for evidence tool-matching tokens from evidence_tool_tokens.csv.

Rule source: intelligence_modules/cim_skill_rag/evidence_tool_tokens.csv
Schema: claim_type, token

Tokens are used for substring matching against a tool's name+source+description
haystack to determine whether a tool can provide evidence for a given ClaimType.
claim_type values correspond to ClaimType enum values (e.g. "runtime_hardware").

Hot-reload: file is re-parsed whenever its mtime changes (canonical pattern
from core/classifier/patterns.py — module-level _cache dict, no lru_cache).

(PIANO 1.0 Schritt 4.0, 2026-06-11)
"""

from __future__ import annotations

import csv
from pathlib import Path

_CSV_PATH = Path(__file__).resolve().parent / "evidence_tool_tokens.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_evidence_tool_tokens() -> dict[str, tuple[str, ...]]:
    """Return token groups keyed by claim_type.

    Returns an empty dict if the CSV file is missing.
    Consumers should treat missing groups as empty tuples via .get(claim_type, ()).
    Re-parses the CSV whenever its mtime changes (hot-reload).
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]
    groups: dict[str, list[str]] = {}
    with _CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            claim_type = str(row.get("claim_type") or "").strip().lower()
            token = str(row.get("token") or "").strip()
            if claim_type and token:
                groups.setdefault(claim_type, []).append(token)
    result: dict[str, tuple[str, ...]] = {ct: tuple(tokens) for ct, tokens in groups.items()}
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
