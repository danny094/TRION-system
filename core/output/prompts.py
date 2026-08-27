from typing import Any, Dict

from core.output.contracts import RenderableEvidence
from core.output.persona_runtime import get_runtime_persona_prompt
from core.output.public_contract_prompt import (
    build_contract_blocks,
    build_verified_evidence_block,
)
from intelligence_modules.prompt_manager import load_prompt


def build_output_system_prompt(
    thinking_plan: Any,
    context: Dict[str, Any],
    *,
    renderable_evidence: tuple[RenderableEvidence, ...] = (),
) -> str:
    parts: list[str] = []
    persona = get_runtime_persona_prompt(context)
    if persona:
        parts.append(persona)
    base = load_prompt("layers", "output")
    if base:
        parts.append(base)
    routing_frame = context.get("routing_frame") if isinstance(context, dict) else None
    parts.extend(
        build_contract_blocks(
            user_text=_user_text(thinking_plan),
            dialogue_act=_dialogue_act(thinking_plan),
            routing_frame=routing_frame,
        )
    )
    plan_block = _plan_block(thinking_plan)
    if plan_block:
        parts.append(plan_block)
    dialogue_block = _dialogue_block(thinking_plan)
    if dialogue_block:
        parts.append(dialogue_block)
    evidence_block = build_verified_evidence_block(renderable_evidence)
    if evidence_block:
        parts.append(evidence_block)
    return "\n\n".join(part for part in parts if part.strip())


def _plan_block(thinking_plan: Any) -> str:
    if thinking_plan is None:
        return ""
    intent = str(getattr(thinking_plan, "intent", "") or "").strip()
    reasoning = str(getattr(thinking_plan, "reasoning", "") or "").strip()
    if not intent:
        return ""
    lines = [f"## Dein Plan\nIntent: {intent}"]
    if reasoning:
        lines.append(f"Reasoning: {reasoning[:400]}")
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        dialogue_act = str(hints.get("dialogue_act") or "").strip()
        response_tone = str(hints.get("response_tone") or "").strip()
        length_hint = str(hints.get("response_length_hint") or "").strip()
        if dialogue_act:
            lines.append(f"DialogueAct: {dialogue_act}")
        if response_tone:
            lines.append(f"ResponseTone: {response_tone}")
        if length_hint:
            lines.append(f"ResponseLengthHint: {length_hint}")
    projection = getattr(thinking_plan, "response_projection", None)
    projection_kind = str(getattr(projection, "kind", "") or "").strip()
    if projection_kind:
        lines.append(f"ResponseProjection: {projection_kind}")
    derivation = getattr(thinking_plan, "response_derivation", None)
    derivation_kind = str(getattr(derivation, "kind", "") or "").strip()
    if derivation_kind:
        lines.append(f"ResponseDerivation: {derivation_kind}")
    evidence_need = getattr(thinking_plan, "additional_evidence_need", None)
    need_reason = str(getattr(evidence_need, "reason", "") or "").strip()
    if need_reason:
        lines.append(f"AdditionalEvidenceNeeded: {need_reason[:240]}")
    return "\n".join(lines)


def _user_text(thinking_plan: Any) -> str:
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("user_text") or "").strip()
    return ""


def _dialogue_act(thinking_plan: Any) -> str:
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("dialogue_act") or "").strip()
    return ""


def _dialogue_block(thinking_plan: Any) -> str:
    dialogue_act = _dialogue_act(thinking_plan).lower()
    if dialogue_act not in {"smalltalk", "feedback", "ack"}:
        return ""
    return load_prompt("contracts", "output_dialogue_rule")
