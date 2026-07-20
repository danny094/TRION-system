from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.task_loop.contracts import StepExecutionStatus, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import (
    AdditionalEvidenceNeed, PlanStep, ResponseDerivation, ResponseProjection,
    RiskLevel, ThinkingPlan,
)
from adapters.task_resume_serialization import plan_from_dict, snapshot_from_dict
from adapters.task_resume_store import (
    claim_waiting_task, finalize_claimed_task, get_task_record, register_waiting_task,
)
from tests.operation_contract_context import canonical_contract_context
from tests.test_task_resume_store import _NoOverrideSettings


def _plan(plan_id, step_id):
    return ThinkingPlan(
        "run", [PlanStep(step_id, "List", "List", tool="inventory")],
        True, RiskLevel.SAFE, plan_id=plan_id,
    )


def _tool():
    return ToolDescriptor(
        "inventory", capability_domain="container_runtime", capability_operation="list",
        capability_evidence_types=["runtime_inventory"], capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )


def test_successful_replan_starts_new_receipt_epoch_and_returns_active_plan():
    original, replanned = _plan("old-plan", "old-step"), _plan("new-plan", "new-step")
    calls = []

    def runner(call):
        calls.append(call.step_id)
        return TaskToolResult(call.step_id == "new-step", {})

    result = build_task_loop_stage(
        original, conversation_id="conv", objective="run", task_loop_fn=start_task_loop,
        tool_runner=runner, replanner_fn=lambda *_args, **_kwargs: replanned,
        max_steps=4, max_retries_per_step=0, max_replans=1,
        available_tools=[_tool()], receipt_tool_descriptors=[_tool()],
        orchestrator_context=canonical_contract_context(allowed_transitions=()),
    ).result

    assert calls == ["old-step", "new-step"]
    assert result.state is TaskLoopState.COMPLETED
    assert result.active_plan is replanned
    assert result.snapshot.plan_id == "new-plan"
    assert result.snapshot.completed_steps == ["new-step"]
    assert len(result.snapshot.step_operation_executions) == 1
    execution = result.snapshot.step_operation_executions[0]
    assert execution.receipt.step_id == "new-step"
    assert execution.status is StepExecutionStatus.SUCCESS


def test_replan_to_answer_resets_old_plan_position_provenance():
    answer = ThinkingPlan("answer", [], False, RiskLevel.SAFE, plan_id="answer-plan")
    result = start_task_loop(
        _plan("old-plan", "old-step"), conversation_id="conv", objective="run",
        tool_runner=lambda _call: TaskToolResult(False, {}),
        replanner_fn=lambda *_args, **_kwargs: answer,
        max_steps=4, max_retries_per_step=0, max_replans=1,
    )
    assert result.active_plan is answer
    assert result.snapshot.plan_id == "answer-plan"
    assert result.snapshot.current_step_index == 0
    assert result.snapshot.completed_steps == []
    assert result.snapshot.step_operation_executions == []


def test_invalid_replan_does_not_partially_switch_execution_epoch():
    invalid = ThinkingPlan(
        "run", [PlanStep("dup", "One", "One", tool="inventory"),
                PlanStep("dup", "Two", "Two", tool="inventory")],
        True, RiskLevel.SAFE, plan_id="invalid-plan",
    )
    result = build_task_loop_stage(
        _plan("old-plan", "old-step"), conversation_id="conv", objective="run",
        task_loop_fn=start_task_loop, tool_runner=lambda _call: TaskToolResult(False, {}),
        replanner_fn=lambda *_args, **_kwargs: invalid,
        max_steps=4, max_retries_per_step=0, max_replans=1,
        available_tools=[_tool()], receipt_tool_descriptors=[_tool()],
        orchestrator_context=canonical_contract_context(allowed_transitions=()),
    ).result
    assert result.state is TaskLoopState.BLOCKED
    assert result.active_plan.plan_id == "old-plan"
    assert result.snapshot.plan_id == "old-plan"
    assert len(result.snapshot.step_operation_executions) == 1
    assert result.snapshot.step_operation_executions[0].receipt.step_id == "old-step"


def test_real_replan_result_roundtrips_through_store_and_resume_parsers(monkeypatch, tmp_path):
    monkeypatch.setattr("config.autonomy.task_resume.settings", _NoOverrideSettings())
    monkeypatch.setenv("AUTONOMY_TASK_RESUME_STORE_PATH", str(tmp_path / "resume.json"))
    original = _plan("old-plan", "old-step")
    replanned = ThinkingPlan(
        "run",
        [PlanStep("new-step", "Inspect", "Inspect", tool="inventory", risk=RiskLevel.NEEDS_CONFIRMATION)],
        True,
        RiskLevel.NEEDS_CONFIRMATION,
        plan_id="new-plan",
        response_projection=ResponseProjection("summary"),
        response_derivation=ResponseDerivation("delayed", seconds=12),
        additional_evidence_need=AdditionalEvidenceNeed(
            "tool", reason="metadata required", candidate_tools=["inventory"],
        ),
    )
    calls = []

    def runner(call):
        calls.append(call.step_id)
        return TaskToolResult(False, {})

    result = build_task_loop_stage(
        original, conversation_id="conv", objective="run", task_loop_fn=start_task_loop,
        tool_runner=runner, replanner_fn=lambda *_args, **_kwargs: replanned,
        max_steps=4, max_retries_per_step=0, max_replans=1,
        available_tools=[_tool()], receipt_tool_descriptors=[_tool()],
        orchestrator_context=canonical_contract_context(allowed_transitions=()),
    ).result
    waiting = result.snapshot.__class__(
        "old-plan", "conv", "run", TaskLoopState.WAITING, 0, 4, 0,
        pending_step="old-step",
    )
    task_id = register_waiting_task(original, waiting)
    claimed = claim_waiting_task(task_id)

    finalized = finalize_claimed_task(task_id, result, expected_updated_at=claimed["updated_at"])
    loaded = get_task_record(task_id)
    loaded_plan = plan_from_dict(loaded["plan"])
    loaded_snapshot = snapshot_from_dict(loaded["snapshot"])

    assert calls == ["old-step"]
    assert finalized["status"] == TaskLoopState.WAITING.value
    assert loaded_plan.plan_id == "new-plan"
    assert loaded_plan == replanned
    assert type(loaded_plan.response_projection) is ResponseProjection
    assert type(loaded_plan.response_derivation) is ResponseDerivation
    assert type(loaded_plan.additional_evidence_need) is AdditionalEvidenceNeed
    assert [step.step_id for step in loaded_plan.steps] == ["new-step"]
    assert loaded_snapshot.current_step_index == 0
    assert loaded_snapshot.completed_steps == []
    assert loaded_snapshot.step_operation_executions == []
    assert loaded_snapshot.pending_step == "new-step"
    assert loaded_snapshot.previous_state is result.snapshot.previous_state
    assert loaded_snapshot.previous_state is TaskLoopState.EXECUTING
    assert "old-step" not in repr((loaded["plan"], loaded["snapshot"]))
