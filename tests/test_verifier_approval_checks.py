from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.approval_checks import run_approval_checks
from core.verifier.contracts import Verdict


def test_run_approval_checks_rejects_needs_confirmation_deploy_without_approval_request():
    plan = ThinkingPlan(
        intent="deploy_container",
        steps=[
            PlanStep(
                step_id="deploy",
                title="Deploy",
                goal="Run deployment",
                tool="deploy_container",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Deploy now.",
        plan_id="plan-1",
    )

    result = run_approval_checks(plan)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "deploy_missing_approval_request"


def test_run_approval_checks_accepts_needs_confirmation_deploy_with_approval_request():
    plan = ThinkingPlan(
        intent="deploy_container",
        steps=[
            PlanStep(step_id="approve", title="Request approval", goal="Ask user", tool="approval_request"),
            PlanStep(
                step_id="deploy",
                title="Deploy",
                goal="Run deployment",
                tool="deploy_container",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Approve then deploy.",
        plan_id="plan-1",
    )

    result = run_approval_checks(plan)

    assert result is None


def test_run_approval_checks_rejects_needs_confirmation_exec_without_approval_request():
    plan = ThinkingPlan(
        intent="operate_container",
        steps=[
            PlanStep(
                step_id="exec",
                title="Run command",
                goal="Execute risky command",
                tool="exec_in_container",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Run command directly.",
        plan_id="plan-1",
    )

    result = run_approval_checks(plan)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "exec_missing_approval_request"


def test_run_approval_checks_accepts_safe_exec_without_approval_request():
    plan = ThinkingPlan(
        intent="operate_container",
        steps=[
            PlanStep(
                step_id="exec",
                title="Run command",
                goal="Execute safe command",
                tool="exec_in_container",
                risk=RiskLevel.SAFE,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Safe command.",
        plan_id="plan-1",
    )

    result = run_approval_checks(plan)

    assert result is None


def test_run_approval_checks_rejects_secret_delete_without_approval_request():
    plan = ThinkingPlan(
        intent="delete_secret",
        steps=[
            PlanStep(
                step_id="delete",
                title="Delete secret",
                goal="Delete target secret",
                tool="secret_delete",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Delete directly.",
        plan_id="plan-1",
    )

    result = run_approval_checks(plan)

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "secret_delete_missing_approval_request"
