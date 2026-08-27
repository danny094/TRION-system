"""Intent- and domain-classification helpers for the routing frame.

`intent_kind` maps the combined signals (classifier category, live claim,
dialogue act, loop markers, domain) onto a coarse intent label used by
gates, capability specs, and the thinking layer.

`domain` maps typed live-claim kinds. Memory-Domain kommt ausschliesslich aus
der vorgelagerten TMR-Projektion.

Loop- und Meta-Tokens kommen aus intelligence_modules; Memory-/Capability-
Rohtexttokens wurden durch die TMR-Projektion ersetzt.

`detect_loop_signals` liest loop_marker- und persistent-Phrasen aus
intelligence_modules/cim_skill_rag/execution_mode_signals_v2.csv (D1-Vollfix).
`intent_kind` liest Meta-Tokens aus intent_classification_tokens.csv. Memory-
Domain und Recall/Search-Intent kommen ausschliesslich aus der vorgelagerten
TMR-Projektion im Routing-Frame-Builder (P11 SP8 R5).
(PIANO 1.0, 2026-06-12)
"""

from __future__ import annotations

from core.classifier.contracts import Category, ClassifierResult
from core.classifier.live_claims import LiveClaimKind

# Ausführungsmodus-Signale (loop_marker + persistent):
# intelligence_modules/cim_skill_rag/execution_mode_signals_v2.csv
# (PIANO 1.0 D1-Vollfix, 2026-06-12 — ersetzt hardcodierte LOOP_MARKERS)
from intelligence_modules.cim_skill_rag.execution_mode_signal_loader import load_execution_mode_signals

# Intent-Klassifizierungs-Tokens (meta_token):
# intelligence_modules/cim_skill_rag/intent_classification_tokens.csv
# (PIANO 1.0 D1-Vollfix; P11 R5 behaelt hier nur META_TOKENS)
from intelligence_modules.cim_skill_rag.intent_classification_loader import load_intent_classification_tokens


def detect_loop_signals(lowered: str) -> bool:
    """Erkennt Loop/Persistenz-Signal vollständig aus CSV.

    Liest loop_marker-Phrasen (kurze Wiederholungs-Marker wie "5x", "mehrfach")
    und persistent-Phrasen (zeitbasierte Dauerbetrieb-Signale wie "täglich")
    aus execution_mode_signals_v2.csv — kein hardcodiertes LOOP_MARKERS-Fallback.
    (D1-Vollfix, 2026-06-12)
    """
    signals = load_execution_mode_signals()
    loop_markers = signals.get("loop_marker", ())
    if any(token in lowered for token in loop_markers):
        return True
    persistent_phrases = signals.get("persistent", ())
    return any(phrase in lowered for phrase in persistent_phrases)


def intent_kind(
    lowered: str,
    classifier_result: ClassifierResult,
    *,
    live_claim: LiveClaimKind,
    dialogue_act: str,
    has_loop_markers: bool,
    domain: str,
) -> str:
    tokens = load_intent_classification_tokens()
    meta_tokens = tokens.get("meta_token", ())
    if any(token in lowered for token in meta_tokens):
        return "meta_analysis"
    if dialogue_act == "feedback":
        return "feedback"
    if dialogue_act in {"smalltalk", "ack"}:
        return "smalltalk"
    if has_loop_markers:
        return "task_loop_request"
    if live_claim == LiveClaimKind.SKILL_INVENTORY:
        return "capability_question"
    if live_claim in {LiveClaimKind.TIME, LiveClaimKind.HARDWARE, LiveClaimKind.FILE_CONTENT, LiveClaimKind.CONTAINER_RUNTIME}:
        return "current_state_question"
    if classifier_result.category in {Category.TOOL, Category.PLANNING}:
        return "action_request"
    return "conceptual_question"


def domain(live_claim: LiveClaimKind) -> str:
    if live_claim == LiveClaimKind.CONTAINER_RUNTIME:
        return "container_runtime"
    if live_claim == LiveClaimKind.FILE_CONTENT:
        return "files"
    if live_claim == LiveClaimKind.HARDWARE:
        return "hardware"
    if live_claim == LiveClaimKind.TIME:
        return "time"
    if live_claim == LiveClaimKind.SKILL_INVENTORY:
        return "tools"
    return "general"
