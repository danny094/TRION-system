from typing import Any

from config import (
    get_output_renderable_evidence_max_bullets_per_item,
    get_output_renderable_evidence_max_items,
)
from core.output.claim_classifier import classify_claim
from core.output.contracts import RenderableEvidence
from core.output.evidence_contracts import ClaimType
from intelligence_modules.prompt_manager import load_prompt


def build_contract_blocks(
    *,
    user_text: str,
    dialogue_act: str,
    routing_frame: Any,
) -> list[str]:
    """Project claim guidance from user intent and the typed routing-frame signal."""
    claim = classify_claim(
        user_text,
        dialogue_act=dialogue_act,
        routing_frame=routing_frame,
    )
    blocks = [load_prompt("contracts", "output_grounding", hybrid_mode_line="")]
    if claim.claim_type in {
        ClaimType.CONCEPTUAL_ANALYSIS,
        ClaimType.RUNTIME_HARDWARE,
        ClaimType.FILE_CONTENT,
    }:
        blocks.append(load_prompt("contracts", "output_analysis_guard"))
    return [block for block in blocks if str(block or "").strip()]


def build_verified_evidence_block(
    renderable_evidence: tuple[RenderableEvidence, ...],
) -> str:
    """Project only OutputStage-produced RenderableEvidence into the LLM prompt."""
    if not renderable_evidence:
        return ""
    if any(type(item) is not RenderableEvidence for item in renderable_evidence):
        raise TypeError("renderable_evidence must contain RenderableEvidence values")
    lines = load_prompt("contracts", "output_evidence_header").splitlines()
    max_items = get_output_renderable_evidence_max_items()
    max_bullets = get_output_renderable_evidence_max_bullets_per_item()
    for item in renderable_evidence[:max_items]:
        if item.summary:
            lines.append(f"- {item.summary}")
        for bullet in item.bullets[:max_bullets]:
            if bullet:
                lines.append(f"  {bullet}")
    return "\n".join(lines) if len(lines) > 2 else ""
