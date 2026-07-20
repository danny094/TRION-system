from core.thinking.contracts import ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import VerifierInput
from core.verifier.rule_loader import load_plan_rules


def run_plan_checks(plan: ThinkingPlan, verifier_input: VerifierInput) -> VerifierResult | None:
    for rule in load_plan_rules():
        result = _evaluate_rule(rule, plan, verifier_input)
        if result:
            return result
    return None


def _evaluate_rule(rule: dict[str, str], plan: ThinkingPlan, verifier_input: VerifierInput) -> VerifierResult | None:
    target_tools = _split(rule.get("target_tools", ""))
    if not target_tools:
        return None
    question_focus = str(verifier_input.document_meta.get("question_focus") or "").strip().lower()
    required_focus = str(rule.get("question_focus") or "").strip().lower()
    for index, step in enumerate(plan.steps):
        tool_name = str(step.tool or "").strip()
        if tool_name not in target_tools:
            continue
        if required_focus and required_focus != question_focus:
            continue
        if not _risk_match(rule.get("step_risk", ""), step.risk.value):
            continue
        if not _command_match(rule.get("command_contains_any", ""), step.tool_arguments):
            continue
        if not _has_any_prior_tool(rule.get("require_any_prior_tool", ""), plan, index):
            return _result_from_rule(rule)
        if not _has_required_step_anywhere(rule.get("required_tools_anywhere", ""), plan):
            return _result_from_rule(rule)
        if _has_required_prior_step(rule.get("required_prior_tools_any", ""), plan, index):
            continue
        return _result_from_rule(rule)
    return None


def _result_from_rule(rule: dict[str, str]) -> VerifierResult:
    verdict_raw = str(rule.get("verdict") or "rejected").strip().lower()
    verdict = Verdict.HARD_BLOCK if verdict_raw == "hard_block" else Verdict.REJECTED
    hint = str(rule.get("hint") or "").strip() or None
    return VerifierResult(
        verdict=verdict,
        hint=hint,
        reason=str(rule.get("reason_code") or rule.get("rule_id") or "plan_rule_triggered").strip(),
        warnings=[f"rule_id={str(rule.get('rule_id') or '').strip()}"],
    )


def _has_required_prior_step(raw_tools: str, plan: ThinkingPlan, index: int) -> bool:
    required = set(_split(raw_tools))
    if not required:
        return True
    prior_tools = {
        str(step.tool or "").strip()
        for step in plan.steps[:index]
        if str(step.tool or "").strip()
    }
    return bool(prior_tools & required)


def _has_any_prior_tool(raw_flag: str, plan: ThinkingPlan, index: int) -> bool:
    if str(raw_flag or "").strip().lower() not in {"1", "true", "yes"}:
        return True
    return any(str(step.tool or "").strip() for step in plan.steps[:index])


def _has_required_step_anywhere(raw_tools: str, plan: ThinkingPlan) -> bool:
    required = set(_split(raw_tools))
    if not required:
        return True
    plan_tools = {
        str(step.tool or "").strip()
        for step in plan.steps
        if str(step.tool or "").strip()
    }
    return bool(plan_tools & required)


def _command_match(raw_terms: str, tool_arguments: dict[str, object]) -> bool:
    terms = _split(raw_terms)
    if not terms:
        return True
    command = str(tool_arguments.get("command") or "").strip().lower()
    return any(term in command for term in terms)


def _risk_match(raw_risk: str, step_risk: str) -> bool:
    required = str(raw_risk or "").strip().lower()
    if not required:
        return True
    return required == str(step_risk or "").strip().lower()


def _split(raw_value: str) -> list[str]:
    return [item.strip().lower() for item in str(raw_value or "").split("|") if item.strip()]
