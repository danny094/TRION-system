from typing import Any, Iterable

# Domain-Matching-Tokens: intelligence_modules/cim_skill_rag/evidence_tool_tokens.csv
# (PIANO 1.0 Schritt 4.0, 2026-06-11)
from intelligence_modules.cim_skill_rag.evidence_tool_loader import load_evidence_tool_tokens

from core.output.capability_questions import is_active_container_capability_question
from core.output.evidence_contracts import ClaimType, EvidenceBundle, EvidenceClaim, GuardDecision


def decide_guard(claim: EvidenceClaim, bundle: EvidenceBundle) -> GuardDecision:
    if claim.claim_type == ClaimType.CONCEPTUAL_ANALYSIS:
        return GuardDecision.ALLOW
    if claim.claim_type == ClaimType.RUNTIME_TIME:
        return _tool_evidence_decision(claim.claim_type, bundle)
    if claim.claim_type == ClaimType.RUNTIME_HARDWARE:
        return _tool_evidence_decision(claim.claim_type, bundle)
    if claim.claim_type == ClaimType.FILE_CONTENT:
        return _tool_evidence_decision(claim.claim_type, bundle)
    if claim.claim_type == ClaimType.CONTAINER_RUNTIME:
        if is_active_container_capability_question(claim.user_text) and _has_verified_scope_evidence(bundle):
            return GuardDecision.ALLOW
        return _tool_evidence_decision(claim.claim_type, bundle)
    if claim.claim_type == ClaimType.SKILL_INVENTORY:
        if _has_verified_self_context_evidence(bundle):
            return GuardDecision.ALLOW
        if _has_tool_evidence(claim.claim_type, bundle):
            return GuardDecision.ALLOW
        return GuardDecision.EXPLICIT_UNKNOWN
    return GuardDecision.ALLOW


def _tool_evidence_decision(claim_type: ClaimType, bundle: EvidenceBundle) -> GuardDecision:
    if _has_tool_evidence(claim_type, bundle):
        return GuardDecision.ALLOW
    return GuardDecision.EXPLICIT_UNKNOWN


def _has_tool_evidence(claim_type: ClaimType, bundle: EvidenceBundle) -> bool:
    live_tools = _live_tool_index(bundle)
    for item in list(bundle.grounded_tool_results or []) + list(bundle.relevant_carryover_results or []):
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or item.get("tool") or "").strip()
        if _is_live_tool_match(tool_name, claim_type, live_tools):
            return True
    return False


def _has_verified_scope_evidence(bundle: EvidenceBundle) -> bool:
    home = bundle.home_context if isinstance(bundle.home_context, dict) else {}
    if home.get("verified") is not True:
        return False
    available = home.get("available_capability_classes")
    return isinstance(available, list) and bool(available)


def _has_verified_self_context_evidence(bundle: EvidenceBundle) -> bool:
    self_context = bundle.self_context if isinstance(bundle.self_context, dict) else {}
    identity = self_context.get("identity") if isinstance(self_context.get("identity"), dict) else {}
    capabilities = self_context.get("capabilities")
    if str(identity.get("status") or "").strip().lower() != "verified":
        return False
    return isinstance(capabilities, list) and bool(capabilities)


def _live_tool_index(bundle: EvidenceBundle) -> dict[str, dict[str, Any]]:
    tools: dict[str, dict[str, Any]] = {}
    for item in list(bundle.available_tool_details or []) + list(bundle.selected_tool_details or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        tools[name] = item
    return tools


def _is_live_tool_match(tool_name: str, claim_type: ClaimType, live_tools: dict[str, dict[str, Any]]) -> bool:
    detail = live_tools.get(str(tool_name or "").strip())
    if not isinstance(detail, dict):
        return False
    name = str(detail.get("name") or "").strip().lower()
    source = str(detail.get("source") or "").strip().lower()
    description = str(detail.get("description") or "").strip().lower()
    haystack = f"{name} {source} {description}"

    tokens = load_evidence_tool_tokens().get(str(claim_type.value).lower(), ())
    if not tokens:
        return False
    return any(token in haystack for token in tokens)
