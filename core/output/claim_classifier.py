# M8 — Evidence Projection (P10 PIANO Signal Layer 1.0, 2026-06-15):
# classify_claim() ist KEIN Routing-Klassifikator. Sie projiziert ein bereits
# im routing_frame enthaltenes live_claim-Signal auf einen ClaimType für die
# Output-Evidence-Prüfung. Die eigentliche Routing-Entscheidung liegt in
# collect_raw_signals() (detect_live_claim_kind → live_claim) und wird via
# routing_frame["source_signals"]["live_claim"] durchgereicht.
#
# C1 Bottleneck-Disziplin: Direktaufruf detect_live_claim_kind ist verboten.
# Routing läuft immer über frame_signals-Capsule (PIANO 1.0, 2026-06-11).
# routing_frame wird von Callern aus OutputRequest.context extrahiert und
# übergeben, damit live_claim_from_frame aus source_signals liest statt
# detect_live_claim_kind neu aufzurufen (Shadow-Authority-Fix, 2026-06-12).
from typing import Any, Dict, Optional

from core.classifier.live_claims import LiveClaimKind
from core.orchestrator.frame_signals import live_claim_from_frame
from core.output.evidence_contracts import ClaimType, EvidenceClaim


def classify_claim(
    user_text: str,
    *,
    dialogue_act: str = "",
    routing_frame: Optional[Dict[str, Any]] = None,
) -> EvidenceClaim:
    if str(dialogue_act or "").strip().lower() in {"smalltalk", "feedback", "ack"}:
        return EvidenceClaim(
            claim_type=ClaimType.CONCEPTUAL_ANALYSIS,
            user_text=user_text,
            required_truth_source="none",
        )
    kind = live_claim_from_frame(routing_frame, user_text)
    if kind == LiveClaimKind.FILE_CONTENT:
        return EvidenceClaim(
            claim_type=ClaimType.FILE_CONTENT,
            user_text=user_text,
            required_truth_source="file_read_tool",
        )
    if kind == LiveClaimKind.HARDWARE:
        return EvidenceClaim(
            claim_type=ClaimType.RUNTIME_HARDWARE,
            user_text=user_text,
            required_truth_source="hardware_runtime_tool",
        )
    if kind == LiveClaimKind.CONTAINER_RUNTIME:
        return EvidenceClaim(
            claim_type=ClaimType.CONTAINER_RUNTIME,
            user_text=user_text,
            required_truth_source="container_runtime_tool",
        )
    if kind == LiveClaimKind.SKILL_INVENTORY:
        return EvidenceClaim(
            claim_type=ClaimType.SKILL_INVENTORY,
            user_text=user_text,
            required_truth_source="skill_or_tool_inventory",
        )
    if kind == LiveClaimKind.TIME:
        return EvidenceClaim(
            claim_type=ClaimType.RUNTIME_TIME,
            user_text=user_text,
            required_truth_source="time_runtime_tool",
        )
    return EvidenceClaim(
        claim_type=ClaimType.CONCEPTUAL_ANALYSIS,
        user_text=user_text,
        required_truth_source="none",
    )
