"""Liest live_claim und dialogue_signal aus routing_frame["source_signals"].

Kein Tool-Auswahl-Code, keine Capability-Logik — nur Signal-Extraktion
mit Fallback auf direkte Berechnung wenn routing_frame absent ist.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.classifier.live_claims import LiveClaimKind, detect_live_claim_kind
from core.dialogue_signal.classifier import classify_dialogue_signal
from core.dialogue_signal.contracts import DialogueSignal


def live_claim_from_frame(
    routing_frame: Optional[Dict[str, Any]], user_text: str
) -> LiveClaimKind:
    """Liest live_claim aus routing_frame; Fallback auf detect_live_claim_kind wenn absent."""
    source_signals = (routing_frame or {}).get("source_signals")
    if isinstance(source_signals, dict):
        raw = source_signals.get("live_claim")
        if raw is not None:
            try:
                return LiveClaimKind(str(raw).strip())
            except ValueError:
                pass
    return detect_live_claim_kind(user_text)


def dialogue_signal_from_frame(
    routing_frame: Optional[Dict[str, Any]], user_text: str
) -> DialogueSignal:
    """Liest dialogue_signal aus routing_frame; Fallback auf classify_dialogue_signal wenn absent."""
    source_signals = (routing_frame or {}).get("source_signals")
    if isinstance(source_signals, dict):
        raw = source_signals.get("dialogue_signal")
        if isinstance(raw, dict):
            return DialogueSignal(
                dialogue_act=str(raw.get("dialogue_act") or "request"),
                response_tone=str(raw.get("response_tone") or "neutral"),
                response_length_hint=str(raw.get("response_length_hint") or "medium"),
                confidence=float(raw.get("confidence") or 0.55),
                classifier_mode=str(raw.get("classifier_mode") or "lexical"),
            )
    return classify_dialogue_signal(user_text)
