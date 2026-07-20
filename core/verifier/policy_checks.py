import json
import re

from core.thinking.contracts import ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import VerifierInput
from core.verifier.rule_loader import load_anti_pattern_rules, load_security_rules


def run_policy_checks(plan: ThinkingPlan, verifier_input: VerifierInput) -> VerifierResult | None:
    return _security_rule_match(_policy_haystack(plan, verifier_input)) or _anti_pattern_match(plan)


def _security_rule_match(haystack: str) -> VerifierResult | None:
    for rule in load_security_rules():
        matches = _matching_terms(rule.get("trigger_keywords", ""), haystack)
        if not matches:
            continue
        action = str(rule.get("verifier_action") or "hard_block").strip().lower()
        verdict = Verdict.REJECTED if action == "reject" else Verdict.HARD_BLOCK
        reason = str(rule.get("reason_code") or rule.get("policy_id") or "security_policy_triggered").strip()
        hint = str(rule.get("hint") or "").strip() or None
        return VerifierResult(
            verdict=verdict,
            hint=hint,
            reason=f"Safety block triggered: {reason}.",
            warnings=[f"policy_id={rule.get('policy_id', '')}", f"matched_terms={','.join(matches[:3])}"],
        )
    return None


def _anti_pattern_match(plan: ThinkingPlan) -> VerifierResult | None:
    haystack = _plan_haystack(plan)
    for rule in load_anti_pattern_rules():
        matches = _matching_terms(rule.get("trigger_keywords", ""), haystack)
        if not matches or not _erroneous_thought_matches(rule.get("erroneous_thought", ""), haystack):
            continue
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint=str(rule.get("correction_rule") or "").strip() or None,
            reason=str(rule.get("pattern_id") or rule.get("pattern_name") or "anti_pattern_triggered").strip(),
            warnings=[f"matched_terms={','.join(matches[:3])}"],
        )
    return None


def _policy_haystack(plan: ThinkingPlan, verifier_input: VerifierInput) -> str:
    payload = {
        "user_text": verifier_input.user_text,
        "document_summary": verifier_input.document_summary,
        "intent": plan.intent,
        "reasoning": plan.reasoning,
        "steps": [
            {
                "title": step.title,
                "goal": step.goal,
                "tool": step.tool,
                "tool_arguments": step.tool_arguments,
            }
            for step in plan.steps
        ],
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True).lower()


def _plan_haystack(plan: ThinkingPlan) -> str:
    parts = [plan.intent, plan.reasoning]
    for step in plan.steps:
        parts.extend([step.title, step.goal, str(step.tool or "")])
    return " ".join(str(part or "").lower() for part in parts)


def _matching_terms(raw_terms: str, haystack: str) -> list[str]:
    return [term for term in _split_terms(raw_terms) if term in haystack]


def _split_terms(raw_terms: str) -> list[str]:
    return [term.strip() for term in (str(raw_terms or "").lower().split("|")) if term.strip()]


def _erroneous_thought_matches(raw_text: str, haystack: str) -> bool:
    tokens = [
        token for token in re.findall(r"[a-zA-Z][a-zA-Z_-]{4,}", str(raw_text or "").lower())
        if token not in {"therefore", "because", "happened", "relationship"}
    ]
    return any(token in haystack for token in tokens[:8])
