"""Routing-frame builder — entry point only.

Wires together the four submodules (intent, evidence, framing, helpers)
and assembles their results into the RoutingFrame dataclass dict.  No
decision logic lives here.

Public API (import path unchanged):
    from core.routing_frame.builder import build_routing_frame
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable

from core.classifier.contracts import ClassifierResult
from core.routing_frame.contracts import RoutingFrame
from core.routing_frame.signal_collector import collect_raw_signals

from core.routing_frame.builder.evidence import evidence_need, execution_mode
from core.routing_frame.builder.framing import confidence, dialogue_style, reasons
from core.routing_frame.builder.helpers import count_items
from core.routing_frame.builder.intent import intent_kind, domain
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.builder.contract_fingerprint import (
    compute_operation_contract_fingerprint,
)
from core.routing_frame.meaning_shadow_trace import sanitize_meaning_for_shadow_trace
from intelligence_modules.cim_skill_rag.meaning_signal_projection_loader import (
    project_meaning_signals,
)

__all__ = ["build_routing_frame"]


def build_routing_frame(
    user_text: str,
    classifier_result: ClassifierResult,
    *,
    available_tool_details: Iterable[Dict[str, Any]] | None = None,
    selected_tool_details: Iterable[Dict[str, Any]] | None = None,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    text = str(user_text or "").strip()
    lowered = text.lower()

    # Phase 1: Rohsignale sammeln (einmalig, deterministisch)
    raw = collect_raw_signals(text, classifier_result, context=context)

    available_count = count_items(available_tool_details)
    selected_count = count_items(selected_tool_details)

    # Phase 2: Normalisierung → RoutingFrame
    projection = project_meaning_signals(raw.meaning)
    dom = projection.get("domain") or domain(raw.live_claim)
    fallback_intent = intent_kind(
        lowered,
        classifier_result,
        live_claim=raw.live_claim,
        dialogue_act=raw.dialogue_signal.dialogue_act,
        has_loop_markers=raw.loop_markers,
        domain=dom,
    )
    intent = projection.get("intent_kind") or fallback_intent
    fallback_evidence = evidence_need(raw.live_claim, domain=dom, intent_kind=intent)
    ev_need = projection.get("evidence_need") or fallback_evidence
    exec_mode = execution_mode(
        classifier_result,
        selected_count=selected_count,
        has_loop_markers=raw.loop_markers,
        domain=dom,
        intent_kind=intent,
        evidence_need_value=ev_need,
    )
    # P11 SP2 (Doc56 A3): operation_contract ist die einzige Operations-/
    # Scope-Wahrheit downstream. requested_operation_family ist nur noch
    # Projektion/Alias von operation_contract.primary_operation (Aufgabe 4).
    # Kein user_text-Parameter im Contract Builder (Aufgabe 2) — ausschliesslich
    # bereits normalisierte Signale (dom/raw.live_claim/intent/ev_need/meaning).
    contract = build_operation_contract(
        domain=dom,
        live_claim=raw.live_claim,
        intent_kind=intent,
        evidence_need=ev_need,
        meaning=raw.meaning,
    )
    contract_fingerprint = compute_operation_contract_fingerprint(contract)
    frame = RoutingFrame(
        intent_kind=intent,
        domain=dom,
        evidence_need=ev_need,
        execution_mode=exec_mode,
        requested_operation_family=contract.primary_operation,
        operation_contract=contract,
        operation_contract_fingerprint=contract_fingerprint,
        dialogue_style=dialogue_style(raw.dialogue_signal.dialogue_act),
        confidence=confidence(
            classifier_result,
            raw.dialogue_signal.confidence,
            selected_count=selected_count,
            has_loop_markers=raw.loop_markers,
        ),
        source_signals={
            "classifier": {
                "category": classifier_result.category.value,
                "route": classifier_result.route.value,
                "needs_orchestrator": classifier_result.needs_orchestrator,
                "confidence": classifier_result.confidence,
                "matched_pattern": classifier_result.matched_pattern,
            },
            "live_claim": raw.live_claim.value,
            "dialogue_signal": {
                "dialogue_act": raw.dialogue_signal.dialogue_act,
                "response_tone": raw.dialogue_signal.response_tone,
                "response_length_hint": raw.dialogue_signal.response_length_hint,
                "confidence": raw.dialogue_signal.confidence,
                "classifier_mode": raw.dialogue_signal.classifier_mode,
            },
            "tool_counts": {
                "available": available_count,
                "selected": selected_count,
            },
            "loop_markers": raw.loop_markers,
            "repeat_count": raw.repeat_count,
            "home_scope_verified": raw.home_scope_verified,
            "self_context_present": raw.self_context_present,
            # P11 SP1 (Doc55 A10): rein diagnostisch. Wird von keiner der
            # obigen Ableitungen (intent/domain/evidence_need/execution_mode/
            # requested_operation_family) gelesen — nur angehaengt, nicht
            # konsumiert. Kein Doc-10-Event (das ist SP7).
            "meaning_shadow_trace": sanitize_meaning_for_shadow_trace(raw.meaning),
        },
        reasons=reasons(
            intent_kind=intent,
            domain=dom,
            evidence_need=ev_need,
            execution_mode=exec_mode,
            has_loop_markers=raw.loop_markers,
            selected_count=selected_count,
        ),
    )
    return asdict(frame)
