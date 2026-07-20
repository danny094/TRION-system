from core.task_loop.contracts import EvidenceArtifact
from core.task_loop.outcome_evaluator import OutcomeAction, evaluate
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def _plan(done_when: str = "") -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=[
            PlanStep(
                step_id="s1",
                title="Step s1",
                goal="Goal s1",
                tool="demo_tool",
                done_when=done_when,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-1",
    )


def test_unknown_done_when_is_not_complete():
    result = evaluate(_plan("future_criterion:xyz"), [], replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


def test_empty_done_when_keeps_no_criteria_complete_behavior():
    result = evaluate(_plan(), [])
    assert result.action == OutcomeAction.COMPLETE


def test_supported_done_when_still_completes_when_met():
    artifacts = [EvidenceArtifact(step_id="s1", artifact_type="file_content")]
    result = evaluate(_plan("file_created"), artifacts)
    assert result.action == OutcomeAction.COMPLETE


def test_file_created_done_when_replans_when_missing():
    artifacts = [EvidenceArtifact(step_id="s1", artifact_type="tool_result")]
    result = evaluate(_plan("file_created"), artifacts, replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


def test_file_created_done_when_blocks_when_budget_exhausted():
    result = evaluate(_plan("file_created"), [], replan_budget_remaining=False)
    assert result.action == OutcomeAction.BLOCK


def test_exit_code_done_when_keeps_existing_matching_behavior():
    artifact = EvidenceArtifact(step_id="s1", artifact_type="tool_result", metadata={"exit_code": "0"})
    result = evaluate(_plan("exit_code:0"), [artifact])
    assert result.action == OutcomeAction.COMPLETE


def test_exit_code_done_when_replans_on_mismatch():
    artifact = EvidenceArtifact(step_id="s1", artifact_type="tool_result", metadata={"exit_code": "1"})
    result = evaluate(_plan("exit_code:0"), [artifact], replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


def test_stdout_contains_done_when_keeps_existing_matching_behavior():
    artifact = EvidenceArtifact(step_id="s1", artifact_type="tool_result", content="All tests: PASSED")
    result = evaluate(_plan("stdout_contains:PASSED"), [artifact])
    assert result.action == OutcomeAction.COMPLETE


def test_stdout_contains_done_when_replans_on_mismatch():
    artifact = EvidenceArtifact(step_id="s1", artifact_type="tool_result", content="FAILED")
    result = evaluate(_plan("stdout_contains:PASSED"), [artifact], replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN


def test_artifact_type_done_when_keeps_existing_matching_behavior():
    artifact = EvidenceArtifact(step_id="s1", artifact_type="semantic_search_result")
    result = evaluate(_plan("artifact_type:semantic_search_result"), [artifact])
    assert result.action == OutcomeAction.COMPLETE


def test_artifact_type_done_when_replans_on_mismatch():
    artifact = EvidenceArtifact(step_id="s1", artifact_type="tool_result")
    result = evaluate(_plan("artifact_type:semantic_search_result"), [artifact], replan_budget_remaining=True)
    assert result.action == OutcomeAction.REPLAN
