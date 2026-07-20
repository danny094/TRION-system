from core.task_loop.contracts import EvidenceArtifact, StepExecutionStatus
from core.task_loop.evidence_adapter import validated_evidence_artifacts
from core.task_loop.executable_now import details_by_name
from core.task_loop.executor import TaskToolResult, execute_step
from core.task_loop.outcome_evaluator import OutcomeAction, evaluate
from core.orchestrator.contracts import ToolDescriptor
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def _step(required_evidence: list[str] | None = None) -> PlanStep:
    return PlanStep(
        step_id="s1",
        title="Inspect",
        goal="Inspect runtime",
        tool="inspect_container",
        tool_arguments={},
        required_evidence=list(required_evidence or []),
    )


def _plan(step: PlanStep) -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect",
        steps=[step],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-1",
    )


def _runner(_call):
    return TaskToolResult(success=True, result={"status": "running"})


def test_tool_success_keeps_tool_result_but_does_not_complete_required_tool_result():
    result = execute_step(
        _step(required_evidence=["tool_result"]),
        _runner,
        tool_details_by_name={"inspect_container": {"name": "inspect_container"}},
    )
    evidence = [EvidenceArtifact.from_dict(item) for item in result.artifacts]

    assert result.status == StepExecutionStatus.SUCCESS
    assert any(item.get("artifact_type") == "tool_result" for item in result.artifacts)
    decision = evaluate(_plan(_step(required_evidence=["tool_result"])), evidence)
    assert decision.action == OutcomeAction.REPLAN


def test_manifest_evidence_type_creates_validated_evidence_artifact():
    artifacts = validated_evidence_artifacts(
        tool_name="inspect_container",
        step_id="s1",
        output={"status": "running"},
        tool_detail={"capability_evidence_types": ["runtime_status"]},
    )

    assert artifacts == [
        {
            "id": "s1-evidence-runtime_status",
            "artifact_type": "runtime_status",
            "tool": "inspect_container",
            "source_step_id": "s1",
            "content": {"status": "running"},
            "metadata": {"validated_evidence": True, "legacy_tool_result": False},
        }
    ]


def test_required_evidence_completes_with_manifest_validated_evidence():
    result = execute_step(
        _step(required_evidence=["runtime_status"]),
        _runner,
        operation_contract_fingerprint="fp-runtime",
        tool_details_by_name={
            "inspect_container": {
                "name": "inspect_container",
                "capability_evidence_types": ["runtime_status"],
            }
        },
    )
    evidence = [EvidenceArtifact.from_dict(item) for item in result.artifacts]

    decision = evaluate(
        _plan(_step(required_evidence=["runtime_status"])),
        evidence,
        expected_operation_contract_fingerprint="fp-runtime",
    )
    assert decision.action == OutcomeAction.COMPLETE


def test_undeclared_evidence_type_does_not_create_validated_evidence():
    artifacts = validated_evidence_artifacts(
        tool_name="inspect_container",
        step_id="s1",
        output={"status": "running"},
        tool_detail={"capability_evidence_types": []},
    )

    assert artifacts == []


def test_tool_descriptor_details_keep_capability_evidence_types():
    details = details_by_name([
        ToolDescriptor(
            name="inspect_container",
            capability_evidence_types=["runtime_status"],
        )
    ])

    assert details["inspect_container"]["capability_evidence_types"] == ["runtime_status"]
