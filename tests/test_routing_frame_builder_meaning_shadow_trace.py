"""P11 SP1 (Codex P1-Fix): meaning_shadow_trace wiring in build_routing_frame.

Ausgelagert aus test_routing_frame_builder.py (Doc07 200-Zeilen-Cap; Codex-
Gegenpruefung). Bewusst kein Import aus einer anderen Testdatei — eigener
lokaler _classifier-Helper, eigene Datei ist die einzige Wahrheit fuer diese
drei Tests.

Die Tests belegen den sanitisierten Trace und die R5-Grenze: Nur vollstaendig
provenance-gebundene, occurrence-genau kartierte TMR-Paare duerfen produktiv
projizieren; unvollstaendig belegte TMR bleibt reine Diagnose.
"""

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.routing_frame.builder import build_routing_frame


def _classifier(
    category: Category = Category.INFORMATION,
    *,
    needs_orchestrator: bool = False,
    route: Route | None = None,
    confidence: float = 0.9,
) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=confidence,
        route=route or (Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING),
        matched_pattern="test",
        reason="test",
    )


def test_meaning_shadow_trace_present_in_source_signals():
    frame = build_routing_frame(
        "Was laeuft zuhause?",
        _classifier(),
    )
    trace = frame["source_signals"]["meaning_shadow_trace"]
    assert trace["status"] == "ok"
    assert trace["predicate"] == "runtime_state"


def test_meaning_shadow_trace_unavailable_does_not_break_frame(monkeypatch):
    def _boom(_text: str):
        raise RuntimeError("defekte Regel-CSV simuliert")

    monkeypatch.setattr(
        "core.routing_frame.meaning.build_meaning_representation", _boom
    )
    frame = build_routing_frame("Was laeuft zuhause?", _classifier())
    assert frame["source_signals"]["meaning_shadow_trace"] == {"status": "unavailable"}


def test_unproven_meaning_never_overrides_routing_decision(monkeypatch):
    """Eine TMR ohne Theme-Provenienz darf keine produktive Projektion tragen."""
    baseline = build_routing_frame(
        "Erklaere mir das Konzept der Versionierung.", _classifier()
    )

    from core.routing_frame.contracts import FieldProvenance, MeaningRepresentation

    def _contradictory(_text: str) -> MeaningRepresentation:
        prov = FieldProvenance(source="test_forced", confidence=0.99)
        return MeaningRepresentation(
            speech_act="request_action",
            predicate="lifecycle_action",
            theme="container",
            roles={},
            scope_candidates=("home",),
            target_candidates=("trion-home",),
            requested_details=(),
            temporal="current",
            polarity="negative",
            modality="must",
            cardinality="all",
            mutation_candidate=True,
            ambiguity=(),
            confidence=0.99,
            provenance={"predicate": prov},
        )

    monkeypatch.setattr(
        "core.routing_frame.meaning.build_meaning_representation", _contradictory
    )
    forced = build_routing_frame(
        "Erklaere mir das Konzept der Versionierung.", _classifier()
    )

    for key in (
        "intent_kind",
        "domain",
        "evidence_need",
        "execution_mode",
        "requested_operation_family",
        "dialogue_style",
        "confidence",
        "reasons",
    ):
        assert forced[key] == baseline[key], key

    forced_trace = forced["source_signals"]["meaning_shadow_trace"]
    assert forced_trace["predicate"] == "lifecycle_action"
    assert forced_trace["mutation_candidate"] is True
