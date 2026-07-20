"""Tests fuer die kanonische Composite-Meaning-Regelquelle."""

from __future__ import annotations

import pytest

from intelligence_modules.cim_skill_rag._meaning_rule_loader import MeaningRuleSchemaError
from intelligence_modules.cim_skill_rag.meaning_composite_loader import (
    load_meaning_composite_rules,
    parse_meaning_composite_rows,
)


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "rule_id": "container_list_logs",
        "language": "de",
        "semantic_sequence": "runtime_state>log_state",
        "intent_sequence": "list>logs",
    }
    row.update(overrides)
    return row


def test_production_composite_rules_load_deterministically():
    first = load_meaning_composite_rules()
    second = load_meaning_composite_rules()

    assert first == second
    assert first[0].semantic_sequence == ("runtime_state", "log_state")
    assert first[0].intent_sequence == ("list", "logs")


def test_parse_rejects_duplicate_rule_id_fail_closed():
    with pytest.raises(MeaningRuleSchemaError):
        parse_meaning_composite_rows([_row(), _row(semantic_sequence="log_state>runtime_state")])


def test_parse_rejects_duplicate_semantic_sequence_fail_closed():
    with pytest.raises(MeaningRuleSchemaError):
        parse_meaning_composite_rows([_row(), _row(rule_id="other_rule")])


def test_parse_rejects_incomplete_sequence_fail_closed():
    with pytest.raises(MeaningRuleSchemaError):
        parse_meaning_composite_rows([_row(semantic_sequence="runtime_state")])


def test_parse_rejects_unknown_semantic_key_fail_closed():
    with pytest.raises(MeaningRuleSchemaError):
        parse_meaning_composite_rows([_row(semantic_sequence="runtime_state>unknown")])


def test_parse_rejects_unknown_intent_fail_closed():
    with pytest.raises(MeaningRuleSchemaError):
        parse_meaning_composite_rows([_row(intent_sequence="list>unknown")])
