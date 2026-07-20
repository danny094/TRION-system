from config import ENABLE_CONTROL_LAYER, SKIP_CONTROL_ON_LOW_RISK
from core.input_processor.contracts import DocumentContext
from core.thinking.contracts import RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import build_verifier_input
from core.verifier.safety import run_safety_check


def run_llm_check(*args, **kwargs):
    from core.verifier.llm_check import run_llm_check as _impl

    return _impl(*args, **kwargs)


def verify_plan(
    plan: ThinkingPlan,
    user_text: str = "",
    *,
    document_context: DocumentContext | None = None,
    autonomous_mode: bool = False,
) -> VerifierResult:
    control_enabled = bool(ENABLE_CONTROL_LAYER or autonomous_mode)
    if not control_enabled:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Verifier ist deaktiviert. Plan-Ausfuehrung bleibt gesperrt, bis die Control-Schicht wieder aktiv ist.",
            reason="control_layer_disabled_fail_closed",
        )

    skip_low_risk = bool(SKIP_CONTROL_ON_LOW_RISK and not autonomous_mode)
    if skip_low_risk and plan.risk_level == RiskLevel.SAFE and not plan.needs_task_loop:
        return VerifierResult(verdict=Verdict.APPROVED, reason="skipped_low_risk")

    verifier_input = build_verifier_input(user_text, plan, document_context=document_context)
    safety_result = run_safety_check(plan, verifier_input)
    if safety_result:
        return safety_result

    return run_llm_check(
        plan,
        verifier_input,
        extra_modes={"task_loop"} if autonomous_mode else None,
    )
