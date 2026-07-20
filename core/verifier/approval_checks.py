from core.thinking.contracts import ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.rule_loader import load_approval_rules


def run_approval_checks(plan: ThinkingPlan) -> VerifierResult | None:
    for rule in load_approval_rules():
        result = _evaluate_rule(rule, plan)
        if result:
            return result
    return None


def _evaluate_rule(rule: dict[str, str], plan: ThinkingPlan) -> VerifierResult | None:
    target_tools = _split(rule.get("target_tools", ""))
    if not target_tools:
        return None
    required_tools = set(_split(rule.get("required_prior_tools_any", "")))
    required_risk = str(rule.get("step_risk") or "").strip().lower()
    for index, step in enumerate(plan.steps):
        tool_name = str(step.tool or "").strip()
        if tool_name not in target_tools:
            continue
        if required_risk and required_risk != str(step.risk.value or "").strip().lower():
            continue
        prior_tools = {
            str(item.tool or "").strip()
            for item in plan.steps[:index]
            if str(item.tool or "").strip()
        }
        if required_tools and prior_tools & required_tools:
            continue
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint=str(rule.get("hint") or "").strip() or None,
            reason=str(rule.get("reason_code") or rule.get("rule_id") or "approval_rule_triggered").strip(),
            warnings=[f"rule_id={str(rule.get('rule_id') or '').strip()}"],
        )
    return None


def _split(raw_value: str) -> list[str]:
    return [item.strip().lower() for item in str(raw_value or "").split("|") if item.strip()]
