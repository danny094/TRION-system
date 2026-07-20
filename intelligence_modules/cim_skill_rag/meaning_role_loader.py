"""Loader for TMR role/scope tokens — P11 SP1 (Doc 55 Mindestinhalt:
"semantische Rollen"; scope_candidates und bekannte Ziel-Aliase werden hier
als eigene `role`-Werte ("scope", "target_alias") mitgefuehrt, statt einer
weiteren Top-Level-Sublayer — siehe P11-Plan Datenquellen/TMR-Regeln).

Rule source: intelligence_modules/cim_skill_rag/meaning_role_tokens.csv
Schema: token, language, role, value (alle Pflichtspalten).

Hot-reload + fail-closed via _meaning_rule_loader.load_rule_rows().
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import load_rule_rows

_CSV_PATH = Path(__file__).resolve().parent / "meaning_role_tokens.csv"
_REQUIRED_COLUMNS = ("token", "language", "role", "value")
_cache: Dict[str, object] = {"mtime": None, "rows": []}


def load_meaning_role_tokens() -> List[Dict[str, str]]:
    """Return role-token rows (token, language, role, value)."""
    return load_rule_rows(_CSV_PATH, _REQUIRED_COLUMNS, _cache)
