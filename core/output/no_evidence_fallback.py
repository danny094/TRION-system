from core.output.claim_classifier import classify_claim
from core.output.contracts import OutputRequest
from core.output.evidence_contracts import GuardDecision
from core.output.evidence_requirements import decide_guard


_UNVERIFIED_FACTS_FALLBACK = "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def apply_no_evidence_fallback(
    output_request: OutputRequest,
    content: str,
    *,
    preflight: bool = False,
) -> str | None:
    if not preflight and not str(content or "").strip():
        return content
    context = output_request.context
    routing_frame = context.get("routing_frame") if isinstance(context, dict) else None
    hints = getattr(output_request.thinking_plan, "context_hints", None)
    dialogue_act = str(hints.get("dialogue_act") or "").strip() if isinstance(hints, dict) else ""
    claim = classify_claim(output_request.user_text, dialogue_act=dialogue_act, routing_frame=routing_frame)
    decision = decide_guard(claim, output_request.output_evidence)
    if decision is GuardDecision.EXPLICIT_UNKNOWN:
        return _UNVERIFIED_FACTS_FALLBACK
    if decision is GuardDecision.LIMIT_TO_VERIFIED and not output_request.renderable_evidence:
        return _UNVERIFIED_FACTS_FALLBACK
    return None if preflight else content
