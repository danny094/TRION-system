from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict
from core.verifier.plan_checks import run_plan_checks
from tests.verifier_plan_test_support import build_verifier_input


def test_run_plan_checks_rejects_stop_container_without_prior_context():
    plan = ThinkingPlan(
        intent="stop_container",
        steps=[PlanStep(step_id="stop", title="Stop container", goal="Stop the target container", tool="stop_container")],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Stop immediately.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "stop_missing_container_context"


def test_run_plan_checks_accepts_stop_container_with_prior_context():
    plan = ThinkingPlan(
        intent="stop_container",
        steps=[
            PlanStep(step_id="list", title="List containers", goal="Inspect running containers", tool="container_list"),
            PlanStep(step_id="stop", title="Stop container", goal="Stop target", tool="stop_container"),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Inspect then stop.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is None


def test_run_plan_checks_rejects_blueprint_delete_without_prior_context():
    plan = ThinkingPlan(
        intent="delete_blueprint",
        steps=[
            PlanStep(
                step_id="delete",
                title="Delete blueprint",
                goal="Delete stale blueprint",
                tool="blueprint_delete",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Delete directly.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "blueprint_mutation_missing_context"


def test_run_plan_checks_rejects_risky_first_operational_step_even_without_specific_context_rule():
    plan = ThinkingPlan(
        intent="operate_container",
        steps=[
            PlanStep(
                step_id="stop",
                title="Stop container",
                goal="Stop target",
                tool="stop_container",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Immediate stop.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason in {"stop_missing_container_context", "risky_step_missing_prior_context"}


def test_run_plan_checks_accepts_risky_step_after_prior_operational_context():
    plan = ThinkingPlan(
        intent="delete_blueprint",
        steps=[
            PlanStep(step_id="bp", title="Get blueprint", goal="Inspect blueprint", tool="blueprint_get"),
            PlanStep(
                step_id="delete",
                title="Delete blueprint",
                goal="Delete stale blueprint",
                tool="blueprint_delete",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Inspect then delete.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is None
