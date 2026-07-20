from core.thinking.contracts import ThinkingPlan
from core.verifier.approval_checks import run_approval_checks
from core.verifier.document_checks import run_document_retrieval_check
from core.verifier.plan_checks import run_plan_checks
from core.verifier.policy_checks import run_policy_checks
from core.verifier.contracts import VerifierResult
from core.verifier.input_prepare import VerifierInput


def run_safety_check(plan: ThinkingPlan, verifier_input: VerifierInput) -> VerifierResult | None:
    retrieval_result = run_document_retrieval_check(plan, verifier_input)
    if retrieval_result:
        return retrieval_result
    plan_result = run_plan_checks(plan, verifier_input)
    if plan_result:
        return plan_result
    approval_result = run_approval_checks(plan)
    if approval_result:
        return approval_result
    return run_policy_checks(plan, verifier_input)
