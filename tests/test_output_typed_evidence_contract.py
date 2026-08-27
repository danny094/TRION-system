from collections.abc import Mapping

import pytest

from adapters.tool_runner_bridge import project_output_evidence_item, project_task_tool_result
from core.pipeline.output_evidence_contracts import (
    OutputEvidenceHandoff,
    OutputEvidenceItem,
    OutputEvidenceState,
    OutputExecutionAttestation,
)
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.task_loop.contracts import CompletionStatus, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import (
    TaskStructuralValidationStatus, TaskToolResult, TaskToolResultStatus, execute_step,
)
from core.task_loop.runner import run_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from mcp.structural_validation_contracts import (
    MCPStructuralValidationResult,
    MCPStructuralValidationStatus,
)
from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)


def _envelope() -> MCPToolResultEnvelope:
    return MCPToolResultEnvelope(
        MCPToolCallStatus.SUCCESS,
        structured_content_presence=MCPResultPresence.VALUE,
        structured_content={"rows": [{"id": 1}]},
        is_error_presence=MCPResultPresence.VALUE,
        is_error=False,
    )


def _step() -> PlanStep:
    return PlanStep("s1", "Inspect", "Inspect", tool="inventory")


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot("plan", "conv", "inspect", TaskLoopState.COMPLETED, 1, 2, 0)


def test_output_evidence_contract_is_deeply_immutable() -> None:
    item = OutputEvidenceItem({"rows": [{"id": 1}]})

    assert isinstance(item.structured_content, Mapping)
    assert item.structured_content["rows"] == ({"id": 1},)
    with pytest.raises(TypeError):
        item.structured_content["other"] = True
    with pytest.raises(TypeError):
        item.structured_content["rows"][0]["id"] = 2


def test_handoff_state_has_explicit_empty_semantics() -> None:
    item = OutputEvidenceItem({"ok": True})

    assert set(OutputEvidenceState) == {
        OutputEvidenceState.NO_TASK_LOOP,
        OutputEvidenceState.TASK_LOOP_INCOMPLETE,
        OutputEvidenceState.COMPLETE_WITHOUT_VALIDATED_EVIDENCE,
        OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
    }
    assert OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP).items == ()
    with pytest.raises(ValueError):
        OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP, (item,))
    with pytest.raises(ValueError):
        OutputEvidenceHandoff(OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE)


def test_projector_accepts_only_valid_p13_structural_results() -> None:
    envelope = _envelope()
    valid = MCPStructuralValidationResult(MCPStructuralValidationStatus.VALID, envelope)
    invalid = MCPStructuralValidationResult(MCPStructuralValidationStatus.INSTANCE_MISMATCH, envelope)

    assert project_output_evidence_item(valid) == OutputEvidenceItem({"rows": [{"id": 1}]})
    assert project_output_evidence_item(invalid) is None
    assert project_output_evidence_item({"structuredContent": {"ok": True}}) is None
    assert project_task_tool_result(envelope, structural_result=valid).structural_validation_status is TaskStructuralValidationStatus.VALID
    assert project_task_tool_result(envelope, structural_result=invalid).structural_validation_status is TaskStructuralValidationStatus.INVALID


def test_success_step_preserves_opaque_structural_result() -> None:
    structural_result = object()
    result = execute_step(
        _step(),
        lambda _call: TaskToolResult(
            status=TaskToolResultStatus.SUCCESS_VALUE,
            result={"ok": True},
            structural_result=structural_result,
        ),
    )

    assert result.structural_result is structural_result


def test_failure_step_and_new_loop_start_without_structural_results() -> None:
    structural_result = object()
    failed = execute_step(
        _step(),
        lambda _call: TaskToolResult(
            status=TaskToolResultStatus.TOOL_FAILURE,
            error="failed",
            structural_result=structural_result,
        ),
    )
    loop_result = TaskLoopResult(TaskLoopState.COMPLETED, None, [], "done", _snapshot())

    assert failed.structural_result is None
    assert loop_result.structural_results == ()


def test_loop_collects_one_structural_slot_per_successful_step() -> None:
    structural_results = {"s1": object(), "s2": object()}
    plan = ThinkingPlan(
        "inspect",
        [_step(), PlanStep("s2", "Inspect again", "Inspect again", tool="inventory")],
        True,
        RiskLevel.SAFE,
        plan_id="plan",
    )
    result = run_task_loop(
        plan,
        TaskLoopSnapshot("plan", "conv", "inspect", TaskLoopState.EXECUTING, 0, 3, 0),
        lambda call: TaskToolResult(
            status=TaskToolResultStatus.SUCCESS_EMPTY,
            structural_result=structural_results[call.step_id],
        ),
    )

    assert result.structural_results == (structural_results["s1"], structural_results["s2"])


def test_loop_preserves_current_epoch_after_later_failure() -> None:
    first = object()
    plan = ThinkingPlan(
        "inspect",
        [_step(), PlanStep("s2", "Fail", "Fail", tool="inventory")],
        True,
        RiskLevel.SAFE,
        plan_id="plan",
    )

    def tool_runner(call):
        if call.step_id == "s1":
            return TaskToolResult(status=TaskToolResultStatus.SUCCESS_EMPTY, structural_result=first)
        return TaskToolResult(status=TaskToolResultStatus.TOOL_FAILURE, error="failed")

    result = run_task_loop(
        plan,
        TaskLoopSnapshot("plan", "conv", "inspect", TaskLoopState.EXECUTING, 0, 3, 0),
        tool_runner,
    )

    assert result.structural_results == (first,)


def test_task_loop_stage_produces_the_only_typed_handoff() -> None:
    plan = ThinkingPlan("inspect", [_step()], True, RiskLevel.SAFE, plan_id="plan")
    loop_result = TaskLoopResult(
        TaskLoopState.COMPLETED,
        None,
        [],
        "done",
        _snapshot(),
        completion_status=CompletionStatus.COMPLETE,
        structural_results=({"ok": True},),
    )
    stage = build_task_loop_stage(
        plan,
        conversation_id="conv",
        objective="inspect",
        task_loop_fn=lambda *_args, **_kwargs: loop_result,
        tool_runner=lambda _call: None,
        replanner_fn=lambda *_args, **_kwargs: None,
        max_steps=2,
        max_retries_per_step=0,
        max_replans=0,
        project_output_evidence_item=lambda value: OutputEvidenceItem(value),
        attest_completed_execution_fn=lambda *_args: OutputExecutionAttestation(("s1",), "fp"),
    )

    assert stage.output_evidence == OutputEvidenceHandoff(
        OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
        (OutputEvidenceItem({"ok": True}),),
    )
