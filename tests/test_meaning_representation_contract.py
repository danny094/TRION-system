"""Contract-Test fuer TRION Meaning Representation (TMR) — P11 SP1.

Prueft gegen docs/architecture/55-trion-meaning-representation.md:
- Schema (Feldnamen/-reihenfolge sind bindend),
- frozen/immutable,
- Provenienz + Konfidenz pro Feld,
- leere statt erfundene Felder,
- kein Toolname, keine Operation in TMR (Doc55 A1 / "TMR darf nicht").
"""

from __future__ import annotations

import dataclasses

import pytest

from core.routing_frame.contracts import (
    CompositeFollowupIntent,
    FieldProvenance,
    MeaningRepresentation,
)

DOC55_FIELD_ORDER = (
    "speech_act",
    "predicate",
    "theme",
    "roles",
    "scope_candidates",
    "target_candidates",
    "requested_details",
    "temporal",
    "polarity",
    "modality",
    "cardinality",
    "mutation_candidate",
    "ambiguity",
    "confidence",
    "provenance",
    "composite_followup",
)


def _empty_meaning_representation() -> MeaningRepresentation:
    return MeaningRepresentation(
        speech_act="",
        predicate="",
        theme="",
        roles={},
        scope_candidates=(),
        target_candidates=(),
        requested_details=(),
        temporal="",
        polarity="",
        modality="",
        cardinality="",
        mutation_candidate=False,
        ambiguity=(),
        confidence=0.0,
        provenance={},
        composite_followup=None,
    )


def test_field_names_match_doc55_exactly():
    field_names = tuple(f.name for f in dataclasses.fields(MeaningRepresentation))
    assert field_names == DOC55_FIELD_ORDER


def test_no_operation_or_tool_field_exists():
    field_names = {f.name for f in dataclasses.fields(MeaningRepresentation)}
    forbidden_substrings = ("operation", "tool")
    for name in field_names:
        for forbidden in forbidden_substrings:
            assert forbidden not in name.lower(), (
                f"MeaningRepresentation.{name} verstoesst gegen Doc55 A1 "
                f"(TMR darf keine Operation/keinen Toolnamen tragen)"
            )


def test_composite_followup_shape_has_no_raw_or_tool_fields():
    followup = CompositeFollowupIntent(
        semantic_sequence=("runtime_state", "log_state"),
        intent_sequence=("list", "logs"),
    )
    field_names = {f.name for f in dataclasses.fields(CompositeFollowupIntent)}
    forbidden_substrings = ("tool", "target", "argument", "evidence", "text", "span")
    for name in field_names:
        assert not any(forbidden in name.lower() for forbidden in forbidden_substrings)
    assert followup.semantic_sequence == ("runtime_state", "log_state")
    assert followup.intent_sequence == ("list", "logs")


def test_is_frozen_immutable():
    mr = _empty_meaning_representation()
    with pytest.raises(dataclasses.FrozenInstanceError):
        mr.predicate = "runtime_state"  # type: ignore[misc]


def test_empty_fields_are_valid_not_hallucinated():
    mr = _empty_meaning_representation()
    assert mr.target_candidates == ()
    assert mr.requested_details == ()
    assert mr.scope_candidates == ()
    assert mr.ambiguity == ()
    assert mr.roles == {}


def test_field_provenance_shape():
    prov = FieldProvenance(source="rule:meaning_concept_tokens", confidence=0.9, span="laeuft")
    assert prov.source == "rule:meaning_concept_tokens"
    assert 0.0 <= prov.confidence <= 1.0
    assert prov.span == "laeuft"


def test_field_provenance_default_span_is_empty():
    prov = FieldProvenance(source="default_empty", confidence=0.0)
    assert prov.span == ""


def test_field_provenance_is_frozen():
    prov = FieldProvenance(source="rule:x", confidence=0.5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        prov.confidence = 1.0  # type: ignore[misc]


def test_provenance_maps_field_name_to_field_provenance():
    mr = MeaningRepresentation(
        speech_act="question",
        predicate="runtime_state",
        theme="container",
        roles={},
        scope_candidates=("home",),
        target_candidates=(),
        requested_details=(),
        temporal="current",
        polarity="",
        modality="",
        cardinality="",
        mutation_candidate=False,
        ambiguity=(),
        confidence=0.8,
        provenance={
            "predicate": FieldProvenance(source="rule:meaning_concept_tokens", confidence=0.9),
            "scope_candidates": FieldProvenance(source="rule:meaning_role_tokens", confidence=0.8, span="zuhause"),
        },
        composite_followup=None,
    )
    assert isinstance(mr.provenance["predicate"], FieldProvenance)
    assert mr.provenance["scope_candidates"].span == "zuhause"
