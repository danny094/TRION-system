"""Guardrail-Tests für core/routing_frame/signal_collector.py — P10/P11 SP1.

T1: collect_raw_signals gibt RawSignals mit allen 8 Feldern zurück
(P11 SP1: `meaning` als zusätzliches Shadow-Feld, siehe Doc55 A10).
"""
from __future__ import annotations

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.classifier.live_claims import LiveClaimKind
from core.dialogue_signal.contracts import DialogueSignal
from core.routing_frame.contracts import MeaningRepresentation, RawSignals
from core.routing_frame.signal_collector import collect_raw_signals


def _make_classifier(category: str = "information") -> ClassifierResult:
    return ClassifierResult(
        category=Category(category),
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=False,
        confidence=0.9,
        route=Route.DIRECT_TO_THINKING,
    )


# ── T1: collect_raw_signals gibt vollständige RawSignals zurück ───────────────

def test_collect_raw_signals_returns_raw_signals_instance():
    """T1a: Rückgabe ist eine RawSignals-Instanz."""
    result = collect_raw_signals("Was ist die aktuelle Uhrzeit?", _make_classifier())
    assert isinstance(result, RawSignals)


def test_collect_raw_signals_all_seven_fields_present():
    """T1b: Alle 7 Kern-Felder (P10) vorhanden und nicht None."""
    result = collect_raw_signals("Was ist die aktuelle Uhrzeit?", _make_classifier())
    assert result.classifier is not None
    assert result.live_claim is not None
    assert result.dialogue_signal is not None
    assert result.loop_markers is not None
    assert result.repeat_count is not None
    assert result.home_scope_verified is not None
    assert result.self_context_present is not None


def test_collect_raw_signals_meaning_is_meaning_representation():
    """P11 SP1: meaning ist eine MeaningRepresentation-Instanz (Shadow-Feld)."""
    result = collect_raw_signals("Was laeuft zuhause?", _make_classifier())
    assert isinstance(result.meaning, MeaningRepresentation)
    assert result.meaning.predicate == "runtime_state"


def test_collect_raw_signals_meaning_failure_does_not_break_raw_signals(monkeypatch):
    """P11 SP1: ein TMR-Fehler darf RawSignals nicht zum Absturz bringen
    (Doc55 A10 — Shadow ist Diagnose, nie Autoritaet)."""
    import core.routing_frame.signal_collector as signal_collector_module

    def _boom(_text: str):
        raise RuntimeError("defekte Regel-CSV simuliert")

    monkeypatch.setattr(
        "core.routing_frame.meaning.build_meaning_representation", _boom
    )
    result = signal_collector_module.collect_raw_signals("Hallo", _make_classifier())
    assert isinstance(result, RawSignals)
    assert result.meaning is None


def test_collect_raw_signals_classifier_is_passed_through():
    """T1c: classifier-Feld enthält exakt den übergebenen ClassifierResult."""
    clf = _make_classifier("tool")
    result = collect_raw_signals("starte container", clf)
    assert result.classifier is clf


def test_collect_raw_signals_live_claim_is_live_claim_kind():
    """T1d: live_claim ist ein LiveClaimKind."""
    result = collect_raw_signals("Wie viel Uhr ist es?", _make_classifier())
    assert isinstance(result.live_claim, LiveClaimKind)
    assert result.live_claim == LiveClaimKind.TIME


def test_collect_raw_signals_dialogue_signal_is_dialogue_signal():
    """T1e: dialogue_signal ist eine DialogueSignal-Instanz."""
    result = collect_raw_signals("Hallo!", _make_classifier("smalltalk"))
    assert isinstance(result.dialogue_signal, DialogueSignal)


def test_collect_raw_signals_loop_markers_bool():
    """T1f: loop_markers ist bool."""
    result = collect_raw_signals("keine Schleife hier", _make_classifier())
    assert isinstance(result.loop_markers, bool)


def test_collect_raw_signals_repeat_count_int():
    """T1g: repeat_count ist int."""
    result = collect_raw_signals("nochmal bitte nochmal", _make_classifier())
    assert isinstance(result.repeat_count, int)


def test_collect_raw_signals_home_scope_verified_false_without_context():
    """T1h: home_scope_verified ist False wenn kein Kontext übergeben."""
    result = collect_raw_signals("Hallo", _make_classifier())
    assert result.home_scope_verified is False


def test_collect_raw_signals_home_scope_verified_true_with_context():
    """T1i: home_scope_verified ist True wenn context["home_context"]["verified"] True."""
    ctx = {"home_context": {"verified": True}}
    result = collect_raw_signals("Hallo", _make_classifier(), context=ctx)
    assert result.home_scope_verified is True


def test_collect_raw_signals_self_context_present_false_without_context():
    """T1j: self_context_present ist False wenn kein self_context im Kontext."""
    result = collect_raw_signals("Hallo", _make_classifier())
    assert result.self_context_present is False


def test_collect_raw_signals_self_context_present_true_with_dict():
    """T1k: self_context_present ist True wenn context["self_context"] ein dict ist."""
    ctx = {"self_context": {"name": "TRION", "version": "1.0"}}
    result = collect_raw_signals("Hallo", _make_classifier(), context=ctx)
    assert result.self_context_present is True
