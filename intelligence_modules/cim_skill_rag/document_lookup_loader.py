"""Lädt Dokument-Lookup-Tokens aus document_lookup_tokens.csv.

Mtime-basiertes Hot-Reload (kein @lru_cache) — canonical pattern
aus core/classifier/patterns.py und anderen IM-Loadern.

PIANO 1.0 B3-Fix: document_policy._is_exact/_semantic/_structure_lookup
lesen jetzt aus dieser Quelle statt hardcodierten Tuples.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

_CSV_PATH = Path(__file__).parent / "document_lookup_tokens.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_document_lookup_tokens() -> Dict[str, Tuple[str, ...]]:
    """Gibt Tokens pro lookup_type zurück.

    Keys: ``exact_lookup``, ``semantic_lookup``, ``structure_lookup``.
    Werte: Tuple von Token-Strings (Kleinschreibung bereits in CSV).
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]

    result: dict[str, list[str]] = {}
    with _CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            token = str(row.get("token") or "").strip()
            lookup_type = str(row.get("lookup_type") or "").strip()
            if token and lookup_type:
                result.setdefault(lookup_type, []).append(token)

    out: Dict[str, Tuple[str, ...]] = {k: tuple(v) for k, v in result.items()}
    _cache["mtime"] = mtime
    _cache["data"] = out
    return out
