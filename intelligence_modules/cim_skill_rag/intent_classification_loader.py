"""Lädt Intent-Klassifizierungs-Tokens aus intent_classification_tokens.csv.

Schema: token, token_type, language
token_types: meta_token

Laedt ausschliesslich die Meta-Tokens fuer
core/routing_frame/builder/intent.py. Memory-Domain und Capability-Test-
Projektion liegen seit P11 SP8 R5 in der TMR-Regelquelle.

Mtime-basiertes Hot-Reload — kein @lru_cache.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple

_CSV_PATH = Path(__file__).parent / "intent_classification_tokens.csv"

_cache: dict[str, object] = {"mtime": None, "data": {}}


def load_intent_classification_tokens() -> Dict[str, Tuple[str, ...]]:
    """Gibt Intent-Klassifizierungs-Tokens gruppiert nach token_type zurück.

    Returns:
        Dict von token_type → Tupel aller Tokens dieses Typs.
        Leer wenn CSV fehlt.
    """
    if not _CSV_PATH.exists():
        return {}
    mtime = _CSV_PATH.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["data"]  # type: ignore[return-value]

    groups: Dict[str, list] = {}
    with _CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            token = str(row.get("token") or "").strip()
            token_type = str(row.get("token_type") or "").strip()
            if token and token_type:
                groups.setdefault(token_type, []).append(token)

    result: Dict[str, Tuple[str, ...]] = {
        t: tuple(tokens) for t, tokens in groups.items()
    }
    _cache["mtime"] = mtime
    _cache["data"] = result
    return result
