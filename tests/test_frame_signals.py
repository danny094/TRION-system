"""Guardrail-Tests für core/orchestrator/frame_signals.py — P10.

T3: live_claim_from_frame ruft detect_live_claim_kind NICHT auf wenn Frame vorhanden.
    Nur wenn Frame absent → Fallback auf detect_live_claim_kind.
"""
from __future__ import annotations

from unittest.mock import patch

from core.classifier.live_claims import LiveClaimKind
from core.orchestrator.frame_signals import live_claim_from_frame, dialogue_signal_from_frame


# ── T3: live_claim_from_frame liest aus Frame, kein detect_live_claim_kind ───

def test_live_claim_from_frame_reads_from_source_signals():
    """T3a: Frame vorhanden → Wert aus source_signals, detect_live_claim_kind nicht aufgerufen."""
    frame = {"source_signals": {"live_claim": "time"}}
    with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
        result = live_claim_from_frame(frame, "irgendein text")
    assert result == LiveClaimKind.TIME
    mock_detect.assert_not_called()


def test_live_claim_from_frame_falls_back_when_frame_none():
    """T3b: Frame None → detect_live_claim_kind wird aufgerufen (Fallback-Capsule)."""
    with patch(
        "core.orchestrator.frame_signals.detect_live_claim_kind",
        return_value=LiveClaimKind.TIME,
    ) as mock_detect:
        result = live_claim_from_frame(None, "Wie viel Uhr ist es?")
    assert result == LiveClaimKind.TIME
    mock_detect.assert_called_once_with("Wie viel Uhr ist es?")


def test_live_claim_from_frame_falls_back_when_source_signals_missing():
    """T3c: Frame ohne source_signals → Fallback-Capsule."""
    frame = {"intent_kind": "current_state_question"}
    with patch(
        "core.orchestrator.frame_signals.detect_live_claim_kind",
        return_value=LiveClaimKind.NONE,
    ) as mock_detect:
        result = live_claim_from_frame(frame, "Hallo")
    mock_detect.assert_called_once()
    assert result == LiveClaimKind.NONE


def test_live_claim_from_frame_invalid_value_falls_back():
    """T3d: Ungültiger live_claim-Wert im Frame → Fallback-Capsule statt Exception."""
    frame = {"source_signals": {"live_claim": "invalid_value_xyz"}}
    with patch(
        "core.orchestrator.frame_signals.detect_live_claim_kind",
        return_value=LiveClaimKind.NONE,
    ) as mock_detect:
        result = live_claim_from_frame(frame, "Hallo")
    mock_detect.assert_called_once()
    assert result == LiveClaimKind.NONE


# ── dialogue_signal_from_frame liest aus Frame ────────────────────────────────

def test_dialogue_signal_from_frame_reads_from_source_signals():
    """T3e: Frame vorhanden → dialogue_signal aus source_signals, classify_dialogue_signal nicht aufgerufen."""
    frame = {
        "source_signals": {
            "dialogue_signal": {
                "dialogue_act": "request",
                "response_tone": "neutral",
                "response_length_hint": "medium",
                "confidence": 0.8,
                "classifier_mode": "lexical",
            }
        }
    }
    with patch("core.orchestrator.frame_signals.classify_dialogue_signal") as mock_classify:
        result = dialogue_signal_from_frame(frame, "irgendein text")
    assert result.dialogue_act == "request"
    mock_classify.assert_not_called()


# ── P10 T6: classify_claim() ist Evidence Projection — kein Shadow-Routing ────

def test_classify_claim_does_not_call_detect_live_claim_kind_when_frame_present():
    """T6: Frame mit live_claim='time' vorhanden → detect_live_claim_kind wird NICHT aufgerufen.
    
    classify_claim() ist eine Evidence-Projection, kein Routing-Klassifikator.
    Wenn der Frame bereits live_claim enthält, darf er es nicht neu berechnen.
    """
    from core.output.claim_classifier import classify_claim
    from core.classifier.live_claims import LiveClaimKind

    frame = {
        "source_signals": {
            "live_claim": "time",
        }
    }
    # Patch auf die Capsule: live_claim_from_frame aus frame_signals ruft detect_live_claim_kind
    # intern auf. Da frame_signals es bereits gebunden hat, muss auf frame_signals gepatcht werden.
    with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
        result = classify_claim("Was ist Python?", routing_frame=frame)
    # Frame-Wert "time" → live_claim_from_frame liest direkt aus source_signals["live_claim"];
    # detect_live_claim_kind wird NICHT aufgerufen.
    mock_detect.assert_not_called()
    # Ergebnis reflektiert TIME-live_claim aus Frame
    assert result.claim_type.value in {"runtime_time", "live_runtime"}
