"""P11-SP8-R5: typed memory-recall routing without raw-text authority."""
from pathlib import Path

from core.classifier.classifier import classify
from core.routing_frame.builder import build_routing_frame
from core.routing_frame.contracts import FieldProvenance, MeaningRepresentation
from core.routing_frame.meaning import build_meaning_representation
from intelligence_modules.cim_skill_rag.meaning_signal_projection_loader import (
    project_meaning_signals,
)


RECALL_PARAPHRASES = (
    "Weisst du noch, was wir zu P10.1 besprochen haben?",
    "Erinnerst du dich an unser P10.1 Thema?",
    "What do you remember about our P10.1 topic?",
)


def _frame(text: str) -> dict:
    return build_routing_frame(text, classify(text))


def test_recall_paraphrases_share_typed_meaning_and_search_contract() -> None:
    for text in RECALL_PARAPHRASES:
        meaning = build_meaning_representation(text)
        frame = _frame(text)

        assert meaning.predicate == "memory_recall"
        assert meaning.theme == "memory"
        assert frame["domain"] == "memory"
        assert frame["intent_kind"] == "current_state_question"
        assert frame["evidence_need"] == "memory_context"
        assert frame["operation_contract"]["primary_operation"] == "search"
        assert frame["operation_contract"]["required_evidence"] == ("memory_context",)


def test_memory_concept_question_does_not_become_recall_search() -> None:
    frame = _frame("Wie funktioniert ein menschliches Gedaechtnis?")

    assert frame["domain"] == "memory"
    assert frame["operation_contract"]["primary_operation"] == ""
    assert frame["operation_contract"]["required_evidence"] == ()


def test_replaced_memory_raw_text_authority_is_absent() -> None:
    intent_source = Path("core/routing_frame/builder/intent.py").read_text(encoding="utf-8")
    token_source = Path(
        "intelligence_modules/cim_skill_rag/intent_classification_tokens.csv"
    ).read_text(encoding="utf-8")

    assert "memory_domain_token" not in intent_source
    assert "capability_test_token" not in intent_source
    assert "memory_domain_token" not in token_source
    assert "capability_test_token" not in token_source


def _recall_meaning(*, predicate_confidence: float, theme_confidence: float, ambiguity=()):
    return MeaningRepresentation(
        predicate="memory_recall",
        theme="memory",
        speech_act="question",
        roles={},
        scope_candidates=(),
        target_candidates=(),
        requested_details=(),
        temporal="current",
        polarity="",
        modality="",
        cardinality="unspecified",
        mutation_candidate=False,
        ambiguity=ambiguity,
        confidence=min(predicate_confidence, theme_confidence),
        provenance={
            "predicate": FieldProvenance("test", predicate_confidence),
            "theme": FieldProvenance("test", theme_confidence),
        },
    )


def test_low_confidence_or_ambiguous_meaning_never_projects() -> None:
    assert project_meaning_signals(
        _recall_meaning(predicate_confidence=0.5, theme_confidence=0.85)
    ) == {}
    assert project_meaning_signals(
        _recall_meaning(predicate_confidence=0.85, theme_confidence=0.5)
    ) == {}
    assert project_meaning_signals(
        _recall_meaning(
            predicate_confidence=0.99,
            theme_confidence=0.99,
            ambiguity=("other_predicate",),
        )
    ) == {}
