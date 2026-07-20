"""Tests fuer die 5 produktiven TMR-Regel-Loader — P11 SP1 Aufgabe 2/3.

Deckt die loader-eigenen Zusatzvalidierungen ab (Aufgabe 3: "Schemafehlern
fail-closed") und prueft, dass die echten CSV-Fixtures unter
intelligence_modules/cim_skill_rag/ fehlerfrei und mit Inhalt laden
(Regression gegen kuenftige CSV-Bearbeitung).
"""

from __future__ import annotations

import pytest

from intelligence_modules.cim_skill_rag._meaning_rule_loader import MeaningRuleSchemaError
from intelligence_modules.cim_skill_rag.meaning_concept_loader import (
    _validate_predicate_or_theme,
    load_meaning_concept_tokens,
)
from intelligence_modules.cim_skill_rag.meaning_detail_loader import load_meaning_detail_tokens
from intelligence_modules.cim_skill_rag.meaning_modifier_loader import (
    _validate_kind,
    load_meaning_modifier_tokens,
)
from intelligence_modules.cim_skill_rag.meaning_role_loader import load_meaning_role_tokens
from intelligence_modules.cim_skill_rag.meaning_signal_projection_loader import (
    load_meaning_signal_projection_rules,
)


def test_validate_predicate_or_theme_accepts_predicate_only():
    _validate_predicate_or_theme({"predicate": "runtime_state", "theme": ""}, 2)


def test_validate_predicate_or_theme_accepts_theme_only():
    _validate_predicate_or_theme({"predicate": "", "theme": "container"}, 2)


def test_validate_predicate_or_theme_rejects_both_empty():
    with pytest.raises(MeaningRuleSchemaError):
        _validate_predicate_or_theme({"predicate": "", "theme": ""}, 2)


def test_validate_kind_accepts_known_kinds():
    for kind in ("polarity", "modality", "temporal"):
        _validate_kind({"modifier_kind": kind}, 2)


def test_validate_kind_rejects_unknown_kind():
    with pytest.raises(MeaningRuleSchemaError):
        _validate_kind({"modifier_kind": "unbekannt"}, 2)


def test_production_concept_csv_loads_with_rows():
    rows = load_meaning_concept_tokens()
    assert len(rows) > 0
    assert all(r.get("predicate") or r.get("theme") for r in rows)


def test_production_role_csv_loads_with_rows():
    rows = load_meaning_role_tokens()
    assert len(rows) > 0
    assert all(r.get("role") in ("scope", "target_alias") or r.get("role") for r in rows)


def test_production_detail_csv_loads_with_rows():
    rows = load_meaning_detail_tokens()
    assert len(rows) > 0


def test_production_modifier_csv_loads_with_rows():
    rows = load_meaning_modifier_tokens()
    assert len(rows) > 0
    assert all(r.get("modifier_kind") in ("polarity", "modality", "temporal") for r in rows)


def test_production_projection_csv_loads_with_rows():
    rows = load_meaning_signal_projection_rules()
    assert len(rows) > 0
    assert all(r.get("predicate") and r.get("theme") for r in rows)
