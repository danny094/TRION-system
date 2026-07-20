"""Loader for TMR concept/predicate tokens — P11 SP1 (Doc 55 Mindestinhalt:
"mehrsprachige Konzepte/Praedikate").

Rule source: intelligence_modules/cim_skill_rag/meaning_concept_tokens.csv
Schema: token, language, predicate, theme (predicate ODER theme darf je
Zeile leer sein, nie beide — manche Tokens tragen nur das Theme bei, z.B.
das blosse Wort "Container").

Hot-reload + fail-closed via _meaning_rule_loader.load_rule_rows().
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import (
    MeaningRuleSchemaError,
    load_rule_rows,
)

_CSV_PATH = Path(__file__).resolve().parent / "meaning_concept_tokens.csv"
_REQUIRED_COLUMNS = ("token", "language")
_cache: Dict[str, object] = {"mtime": None, "rows": []}


def _validate_predicate_or_theme(row: Dict[str, str], line_no: int) -> None:
    if not row.get("predicate") and not row.get("theme"):
        raise MeaningRuleSchemaError(
            f"{_CSV_PATH.name}:{line_no}: weder 'predicate' noch 'theme' gesetzt"
        )


def load_meaning_concept_tokens() -> List[Dict[str, str]]:
    """Return concept-token rows (token, language, predicate, theme).

    Leere Datei/fehlende Datei -> leere Liste (kein Fehler, siehe
    _meaning_rule_loader-Docstring). Schemafehler -> MeaningRuleSchemaError.
    """
    return load_rule_rows(
        _CSV_PATH,
        _REQUIRED_COLUMNS,
        _cache,
        row_validator=_validate_predicate_or_theme,
    )
