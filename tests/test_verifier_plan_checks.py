from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict
from core.verifier.plan_checks import run_plan_checks
from tests.verifier_plan_test_support import build_verifier_input


def test_run_plan_checks_rejects_deploy_without_blueprint_validation():
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

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "deploy_missing_blueprint_validation"


def test_run_plan_checks_accepts_deploy_with_blueprint_validation():
    plan = ThinkingPlan(
        intent="deploy_container",
        steps=[
            PlanStep(step_id="bp", title="Read blueprint", goal="Inspect blueprint", tool="blueprint_get"),
            PlanStep(step_id="deploy", title="Deploy", goal="Run deployment", tool="deploy_container"),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Validate then deploy.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is None


def test_run_plan_checks_rejects_risky_exec_without_container_inspection():
    plan = ThinkingPlan(
        intent="repair_container",
        steps=[
            PlanStep(
                step_id="exec",
                title="Execute command",
                goal="Run shell command",
                tool="exec_in_container",
                tool_arguments={"command": "rm -rf /tmp/cache"},
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Execute quickly.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "exec_missing_container_inspection"


def test_run_plan_checks_accepts_risky_exec_after_container_inspection():
    plan = ThinkingPlan(
        intent="repair_container",
        steps=[
            PlanStep(step_id="inspect", title="Inspect", goal="Inspect container", tool="container_inspect"),
            PlanStep(
                step_id="exec",
                title="Execute command",
                goal="Run shell command",
                tool="exec_in_container",
                tool_arguments={"command": "rm -rf /tmp/cache"},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Inspect first.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is None


def test_run_plan_checks_rejects_exact_document_question_without_workspace_read():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic",
                title="Search chunk",
                goal="Find the quote",
                tool="memory_semantic_search",
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Search only.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input(focus="exact"))

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "exact_lookup_missing_workspace_read"


def test_run_plan_checks_accepts_exact_document_question_with_workspace_read():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(step_id="semantic", title="Search chunk", goal="Find the quote", tool="memory_semantic_search"),
            PlanStep(
                step_id="read",
                title="Read chunk",
                goal="Read exact passage",
                tool="workspace_get",
                tool_arguments={"entry_id": 101},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Search then read.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input(focus="exact"))

    assert result is None
