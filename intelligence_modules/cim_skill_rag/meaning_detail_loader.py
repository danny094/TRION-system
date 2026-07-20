"""Loader for TMR detail-field tokens — P11 SP1 (Doc 55 Mindestinhalt:
"Detailfelder").

Rule source: intelligence_modules/cim_skill_rag/meaning_detail_tokens.csv
Schema: token, language, detail (alle Pflichtspalten).

Hot-reload + fail-closed via _meaning_rule_loader.load_rule_rows().
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import load_rule_rows

_CSV_PATH = Path(__file__).resolve().parent / "meaning_detail_tokens.csv"
_REQUIRED_COLUMNS = ("token", "language", "detail")
_cache: Dict[str, object] = {"mtime": None, "rows": []}


def load_meaning_detail_tokens() -> List[Dict[str, str]]:
    """Return detail-token rows (token, language, detail)."""
    return load_rule_rows(_CSV_PATH, _REQUIRED_COLUMNS, _cache)
