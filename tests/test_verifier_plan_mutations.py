from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict
from core.verifier.plan_checks import run_plan_checks
from tests.verifier_plan_test_support import build_verifier_input


def test_run_plan_checks_rejects_workspace_update_without_prior_context():
    plan = ThinkingPlan(
        intent="update_workspace",
        steps=[PlanStep(step_id="update", title="Update workspace", goal="Rewrite note", tool="workspace_update")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Update directly.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "workspace_mutation_missing_context"


def test_run_plan_checks_accepts_workspace_update_with_prior_context():
    plan = ThinkingPlan(
        intent="update_workspace",
        steps=[
            PlanStep(step_id="get", title="Read workspace", goal="Inspect note", tool="workspace_get"),
            PlanStep(step_id="update", title="Update workspace", goal="Rewrite note", tool="workspace_update"),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Read then update.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is None


def test_run_plan_checks_rejects_conversation_meta_upsert_without_prior_context():
    plan = ThinkingPlan(
        intent="update_conversation_meta",
        steps=[
            PlanStep(
                step_id="meta",
                title="Update conversation metadata",
                goal="Change metadata",
                tool="conversation_meta_upsert",
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Write directly.",
        plan_id="plan-1",
    )

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "conversation_meta_update_missing_context"


def test_run_plan_checks_rejects_secret_delete_without_prior_context():
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

    result = run_plan_checks(plan, build_verifier_input())

    assert result is not None
    assert result.verdict == Verdict.REJECTED
    assert result.reason == "secret_delete_missing_context"


def test_run_plan_checks_accepts_secret_delete_with_prior_context():
    plan = ThinkingPlan(
        intent="delete_secret",
        steps=[
            PlanStep(step_id="list", title="List secrets", goal="Inspect secret names", tool="secret_list"),
            PlanStep(
                step_id="delete",
                title="Delete secret",
                goal="Delete target secret",
                tool="secret_delete",
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
