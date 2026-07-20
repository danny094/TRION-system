"""Loader for canonical composite TMR follow-up rules.

Rule source: intelligence_modules/cim_skill_rag/meaning_composite_rules.csv.
The CSV is the only canonical source for explicit ordered composite meaning.
It stores semantic predicate keys and semantic operation intents, never user
texts, tool names, targets, arguments, evidence, artifacts, or runtime data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from intelligence_modules.cim_skill_rag._meaning_rule_loader import (
    MeaningRuleSchemaError,
    load_rule_rows,
)
from intelligence_modules.cim_skill_rag.meaning_concept_loader import (
    load_meaning_concept_tokens,
)

_CSV_PATH = Path(__file__).resolve().parent / "meaning_composite_rules.csv"
_REQUIRED_COLUMNS = ("rule_id", "language", "semantic_sequence", "intent_sequence")
_KNOWN_INTENTS = (
    "search",
    "read",
    "list",
    "inspect",
    "logs",
    "write",
    "update",
    "delete",
    "execute",
    "maintain",
)
_cache: Dict[str, object] = {"mtime": None, "rows": []}


@dataclass(frozen=True)
class CompositeMeaningRule:
    rule_id: str
    language: str
    semantic_sequence: Tuple[str, ...]
    intent_sequence: Tuple[str, ...]


def _split_sequence(raw: str) -> Tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(">") if part.strip())


def _known_predicates() -> Tuple[str, ...]:
    rows = load_meaning_concept_tokens()
    return tuple(sorted({row.get("predicate", "") for row in rows if row.get("predicate")}))


def parse_meaning_composite_rows(
    rows: Iterable[Dict[str, str]],
    *,
    source_name: str = _CSV_PATH.name,
) -> List[CompositeMeaningRule]:
    known_predicates = set(_known_predicates())
    seen_ids: set[str] = set()
    seen_semantics: set[Tuple[str, ...]] = set()
    parsed: List[CompositeMeaningRule] = []

    for index, row in enumerate(rows, start=2):
        semantic_sequence = _split_sequence(row.get("semantic_sequence", ""))
        intent_sequence = _split_sequence(row.get("intent_sequence", ""))
        if len(semantic_sequence) < 2 or len(intent_sequence) < 2:
            raise MeaningRuleSchemaError(f"{source_name}:{index}: Sequenz zu kurz")
        unknown_predicates = [item for item in semantic_sequence if item not in known_predicates]
        if unknown_predicates:
            raise MeaningRuleSchemaError(
                f"{source_name}:{index}: unbekannte Predicate {unknown_predicates}"
            )
        unknown_intents = [item for item in intent_sequence if item not in _KNOWN_INTENTS]
        if unknown_intents:
            raise MeaningRuleSchemaError(
                f"{source_name}:{index}: unbekannte Intents {unknown_intents}"
            )
        rule_id = row.get("rule_id", "")
        if rule_id in seen_ids:
            raise MeaningRuleSchemaError(f"{source_name}:{index}: doppelte rule_id")
        if semantic_sequence in seen_semantics:
            raise MeaningRuleSchemaError(f"{source_name}:{index}: doppelte Semantic-Sequenz")
        seen_ids.add(rule_id)
        seen_semantics.add(semantic_sequence)
        parsed.append(
            CompositeMeaningRule(
                rule_id=rule_id,
                language=row.get("language", ""),
                semantic_sequence=semantic_sequence,
                intent_sequence=intent_sequence,
            )
        )
    return parsed


def load_meaning_composite_rules() -> List[CompositeMeaningRule]:
    rows = load_rule_rows(_CSV_PATH, _REQUIRED_COLUMNS, _cache)
    return parse_meaning_composite_rows(rows)
