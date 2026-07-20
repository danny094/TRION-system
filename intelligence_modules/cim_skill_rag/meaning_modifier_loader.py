"""Loader for TMR negation/modality/temporal tokens — P11 SP1 (Doc 55
Mindestinhalt: "Negation/Modalitaet/Zeit").

Rule source: intelligence_modules/cim_skill_rag/meaning_modifier_tokens.csv
Schema: token, language, modifier_kind, modifier_value (alle Pflichtspalten).
`modifier_kind` in {polarity, modality, temporal}.

Hot-reload + fail-closed via _meaning_rule_loader.load_rule_rows().
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import (
    MeaningRuleSchemaError,
    load_rule_rows,
)

_CSV_PATH = Path(__file__).resolve().parent / "meaning_modifier_tokens.csv"
_REQUIRED_COLUMNS = ("token", "language", "modifier_kind", "modifier_value")
_VALID_KINDS = {"polarity", "modality", "temporal"}
_cache: Dict[str, object] = {"mtime": None, "rows": []}


def _validate_kind(row: Dict[str, str], line_no: int) -> None:
    if row.get("modifier_kind") not in _VALID_KINDS:
        raise MeaningRuleSchemaError(
            f"{_CSV_PATH.name}:{line_no}: unbekannter modifier_kind "
            f"'{row.get('modifier_kind')}' (erlaubt: {sorted(_VALID_KINDS)})"
        )


def load_meaning_modifier_tokens() -> List[Dict[str, str]]:
    """Return modifier-token rows (token, language, modifier_kind, modifier_value)."""
    return load_rule_rows(
        _CSV_PATH, _REQUIRED_COLUMNS, _cache, row_validator=_validate_kind
    )
