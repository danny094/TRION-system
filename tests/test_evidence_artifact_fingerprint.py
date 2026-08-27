from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.task_loop.contracts import EvidenceArtifact, TaskLoopState
from core.task_loop.evidence_adapter import validated_evidence_artifacts
from core.task_loop.executor import TaskStructuralValidationStatus, TaskToolResult
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.operation_contract_context import canonical_contract_context


def _detail() -> dict[str, object]:
    return {"capability_evidence_types": ["runtime_status"]}


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect",
        steps=[
            PlanStep(
                step_id="s1",
                title="Inspect",
                goal="Inspect runtime",
                tool="inspect_container",
                tool_arguments={},
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-1",
    )


def test_evidence_adapter_stamps_operation_contract_fingerprint():
    artifacts = validated_evidence_artifacts(
        tool_name="inspect_container",
        step_id="s1",
        output={"status": "running"},
        tool_detail=_detail(),
        operation_contract_fingerprint="fp-123",
        structural_result=object(),
        structural_validation_status=TaskStructuralValidationStatus.VALID,
    )

    assert artifacts[0]["metadata"]["validated_evidence"] is True
    assert artifacts[0]["metadata"]["operation_contract_fingerprint"] == "fp-123"


def test_evidence_adapter_does_not_set_fake_fingerprint():
    artifacts = validated_evidence_artifacts(
        tool_name="inspect_container",
        step_id="s1",
        output={"status": "running"},
        tool_detail=_detail(),
        structural_result=object(),
        structural_validation_status=TaskStructuralValidationStatus.VALID,
    )

    assert artifacts[0]["metadata"]["validated_evidence"] is True
    assert "operation_contract_fingerprint" not in artifacts[0]["metadata"]


def test_task_loop_stage_stamps_evidence_from_routing_frame_fingerprint():
    def runner(_call):
        return TaskToolResult(
            success=True,
            result={"status": "running"},
            structural_result=object(),
            structural_validation_status=TaskStructuralValidationStatus.VALID,
        )

    context = canonical_contract_context(
        primary_operation="inspect", allowed_operations=("inspect",),
        allowed_transitions=(), required_evidence=("runtime_status",),
    )
    fingerprint = context["routing_frame"]["operation_contract_fingerprint"]
    stage = build_task_loop_stage(
        _plan(),
        conversation_id="conv-1",
        objective="Inspect runtime",
        task_loop_fn=start_task_loop,
        tool_runner=runner,
        replanner_fn=None,
        max_steps=3,
        max_retries_per_step=0,
        max_replans=0,
        available_tools=[
            ToolDescriptor(
                name="inspect_container",
                capability_domain="container_runtime",
                capability_operation="inspect",
                capability_evidence_types=["runtime_status"],
                capability_required_args=[],
                capability_target_scopes=["runtime_state"],
                capability_risk="read_only",
            )
        ],
        orchestrator_context=context,
    )

    assert stage.result.state == TaskLoopState.COMPLETED
    evidence = [
        item
        for item in stage.result.artifacts
        if item.get("artifact_type") == "runtime_status"
    ][0]
    tool_result = [
        item
        for item in stage.result.artifacts
        if item.get("artifact_type") == "tool_result"
    ][0]
    assert evidence["metadata"]["operation_contract_fingerprint"] == fingerprint
    assert "metadata" not in tool_result


def test_evidence_artifact_roundtrip_preserves_fingerprint_metadata():
    artifact = EvidenceArtifact.from_dict(
        {
            "source_step_id": "s1",
            "artifact_type": "runtime_status",
            "content": "ok",
            "metadata": {
                "validated_evidence": True,
                "operation_contract_fingerprint": "fp-123",
            },
        }
    )

    assert artifact.metadata["operation_contract_fingerprint"] == "fp-123"
