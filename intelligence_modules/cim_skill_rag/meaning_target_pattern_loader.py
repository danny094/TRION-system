"""Fail-closed hot-reload loader for generic TMR target patterns."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from intelligence_modules.cim_skill_rag._meaning_rule_loader import (
    MeaningRuleSchemaError,
    load_rule_rows,
)

_CSV_PATH = Path(__file__).resolve().parent / "meaning_target_patterns.csv"
_REQUIRED_COLUMNS = ("pattern", "language")
_cache: Dict[str, object] = {"mtime": None, "rows": []}


def _validate_pattern(row: Dict[str, str], line_no: int) -> None:
    try:
        compiled = re.compile(row["pattern"], re.IGNORECASE)
    except re.error as exc:
        raise MeaningRuleSchemaError(
            f"{_CSV_PATH.name}:{line_no}: invalid target pattern"
        ) from exc
    if "target" not in compiled.groupindex:
        raise MeaningRuleSchemaError(
            f"{_CSV_PATH.name}:{line_no}: missing named target group"
        )


def load_meaning_target_patterns() -> List[Dict[str, str]]:
    """Return validated target-pattern rows without making target decisions."""
    return load_rule_rows(
        _CSV_PATH,
        _REQUIRED_COLUMNS,
        _cache,
        row_validator=_validate_pattern,
    )
