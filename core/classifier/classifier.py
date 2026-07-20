from config import CHUNKING_THRESHOLD, ENABLE_CHUNKING
from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.classifier.live_claims import LiveClaimKind, detect_live_claim_kind
from core.classifier.patterns import PatternMatch, match as match_policy

_CATEGORY_MAP = {
    "calculation": Category.TOOL, "data_processing": Category.TOOL,
    "planning": Category.PLANNING, "file_system": Category.TOOL,
    "information": Category.INFORMATION, "maintenance": Category.TOOL,
    "security": Category.RISK, "meta_creation": Category.TOOL,
}
_NON_TOOL_ACTIONS = {"deny_autonomy", "fallback_chat", ""}


def classify(user_text: str) -> ClassifierResult:
    estimated_tokens = _estimate_input_tokens(user_text)
    long_doc = ENABLE_CHUNKING and estimated_tokens >= CHUNKING_THRESHOLD
    matched = match_policy(user_text)
    if matched is None:
        return _default_result(user_text, estimated_tokens, long_doc)
    return _result_from_pattern(matched, estimated_tokens, long_doc)


def _default_result(user_text: str, tokens: int, long_doc: bool) -> ClassifierResult:
    return _live_claim_default_result(user_text, tokens, long_doc) or ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=False,
        confidence=1.0,
        route=Route.DIRECT_TO_THINKING,
        matched_pattern="default_no_match",
        reason="No policy pattern matched; routing as plain information request.",
        is_long_document=long_doc,
        estimated_input_tokens=tokens,
    )


def _live_claim_default_result(user_text: str, tokens: int, long_doc: bool) -> ClassifierResult | None:
    kind = detect_live_claim_kind(user_text)
    if kind == LiveClaimKind.NONE:
        return None
    return ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=True,
        confidence=0.85,
        route=Route.NEEDS_ORCHESTRATOR,
        matched_pattern=f"live_claim_{kind.value}",
        reason="Detected a live factual claim that requires runtime discovery and verified evidence.",
        is_long_document=long_doc,
        estimated_input_tokens=tokens,
    )


def _result_from_pattern(matched: PatternMatch, tokens: int, long_doc: bool) -> ClassifierResult:
    category = _CATEGORY_MAP.get(matched.trigger_category, Category.UNKNOWN)
    safety = _safety_from(matched)
    route = _route_from(safety, matched)
    return ClassifierResult(
        category=category,
        safety_level=safety,
        needs_orchestrator=(route == Route.NEEDS_ORCHESTRATOR),
        confidence=matched.confidence,
        route=route,
        matched_pattern=matched.pattern_id,
        reason=f"Matched policy {matched.pattern_id} (trigger={matched.trigger_category}, safety={matched.safety_level}).",
        is_long_document=long_doc,
        estimated_input_tokens=tokens,
    )


def _safety_from(matched: PatternMatch) -> SafetyLevel:
    level = matched.safety_level.lower()
    if level == "critical":
        return SafetyLevel.BLOCK
    if level in ("high", "medium") or matched.requires_confirmation:
        return SafetyLevel.WARNING
    return SafetyLevel.SAFE


def _route_from(safety: SafetyLevel, matched: PatternMatch) -> Route:
    if safety == SafetyLevel.BLOCK:
        return Route.BLOCK
    actions = {matched.action_if_missing, matched.action_if_present}
    if "deny_autonomy" in actions:
        return Route.BLOCK
    if actions - _NON_TOOL_ACTIONS:
        return Route.NEEDS_ORCHESTRATOR
    return Route.DIRECT_TO_THINKING


def _estimate_input_tokens(user_text: str) -> int:
    text = str(user_text or "").strip()
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
