"""Signal Collector — Rohsignale sammeln (keine Normalisierung).

Sammelt alle Rohsignale einmalig an einem Ort und gibt sie als
RawSignals zurück. Semantische Frame-Felder (intent_kind, domain,
evidence_need) bleiben Aufgabe des RoutingFrameBuilder.

P11-Erweiterungspunkt: Tool-Discovery-Signale kommen als weiterer
Parameter hinzu — in P10 kein available_tool_details.
"""

from __future__ import annotations

from typing import Any, Dict

from core.classifier.contracts import ClassifierResult
from core.classifier.live_claims import detect_live_claim_kind
from core.dialogue_signal.classifier import classify_dialogue_signal
from core.routing_frame.contracts import MeaningRepresentation, RawSignals


def _build_meaning_signal_safely(text: str) -> "MeaningRepresentation | None":
    """Build the typed TMR input for projection and sanitized tracing.

    Ein Fehler im TMR-Aufbau darf den produktiven Aufbau von RawSignals nicht
    blockieren: meaning bleibt dann None, sodass Projektion und Trace
    fail-closed bleiben.
    """
    try:
        from core.routing_frame.meaning import build_meaning_representation

        return build_meaning_representation(text)
    except Exception:
        return None


def collect_raw_signals(
    user_text: str,
    classifier_result: ClassifierResult,
    *,
    context: Dict[str, Any] | None = None,
) -> RawSignals:
    """Rohsignale sammeln — einmalig, deterministisch, ohne Normalisierung.

    Args:
        user_text: Rohe Useranfrage.
        classifier_result: Ergebnis des Control-Classifiers.
        context: Optionaler Kontext (home_context, self_context).

    Returns:
        RawSignals mit allen 8 Feldern befüllt. `meaning` wird genau einmal
        durch den R5-Projektionsowner gelesen und weiterhin sanitisiert nach
        source_signals["meaning_shadow_trace"] gespiegelt.

    Hinweis: builder.helpers und builder.intent werden lazy importiert,
    um einen Circular-Import mit builder/__init__.py zu vermeiden.
    """
    # Lazy imports — builder/__init__ importiert dieses Modul, daher
    # kein Top-Level-Import aus core.routing_frame.builder.*
    from core.routing_frame.builder.helpers import repeat_count
    from core.routing_frame.builder.intent import detect_loop_signals

    text = str(user_text or "").strip()
    lowered = text.lower()
    ctx = context or {}

    return RawSignals(
        classifier=classifier_result,
        live_claim=detect_live_claim_kind(text),
        dialogue_signal=classify_dialogue_signal(text),
        loop_markers=detect_loop_signals(lowered),
        repeat_count=repeat_count(lowered),
        home_scope_verified=bool(
            (ctx.get("home_context") or {}).get("verified") is True
        ),
        self_context_present=isinstance(ctx.get("self_context"), dict),
        meaning=_build_meaning_signal_safely(text),
    )
