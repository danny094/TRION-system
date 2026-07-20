from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_replan_trace, emit_task_loop_state
from core.task_loop.replan_contract_block import blocked_replan_result
from core.thinking.contracts import AdditionalEvidenceNeed, PlanStep, RiskLevel, ThinkingPlan


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="inspect",
        state=TaskLoopState.REPLANNING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=3,
        replan_count=2,
        no_progress_count=1,
        total_steps=4,
        tool_calls=3,
        max_total_steps=8,
        max_tool_calls=5,
        deadline_ts=1234.5,
        artifacts=[{"artifact_type": "tool_result", "content": "secret"}],
    )


def test_task_loop_state_exposes_runtime_budgets():
    events = []
    emit_task_loop_state(events.append, _snapshot(), total_steps=1)

    event = events[0]
    assert event["replan_count"] == 2
    assert event["max_replans"] == 3
    assert event["max_steps"] == 5
    assert event["no_progress_count"] == 1
    assert event["run_total_steps"] == 4
    assert event["tool_calls"] == 3
    assert event["max_total_steps"] == 8
    assert event["max_tool_calls"] == 5
    assert event["deadline_set"] is True
    provenance = next(item for item in events if item.get("type") == "task_loop_provenance")
    assert provenance["validated_evidence_types"] == []
    assert provenance["generic_tool_result_count"] == 1
    assert "deadline_ts" not in event
    assert "1234.5" not in repr(event)


def test_plan_contract_replan_block_omits_free_waiting_values():
    events = []

    result = blocked_replan_result(
        _snapshot(),
        events.append,
        "plan_contract_unknown_tool:PRIVATE_TOOL_SENTINEL",
        total_steps=1,
    )

    event = events[0]
    assert result.state == TaskLoopState.BLOCKED
    assert result.stop_reason == StopReason.CAPABILITY_GAP
    assert event["type"] == "task_loop_state"
    assert "waiting_source" not in event
    assert "waiting_reason" not in event
    provenance = next(item for item in events if item.get("type") == "task_loop_provenance")
    assert provenance["validator_decision"] == "blocked"
    assert "PRIVATE_TOOL_SENTINEL" not in repr(event)
    assert "secret" not in repr(event)


def test_replan_trace_is_structured_and_omits_values_and_artifact_content():
    events = []
    plan = ThinkingPlan(
        intent="inspect containers",
        steps=[PlanStep(
            step_id="inspect-1",
            title="Inspect",
            goal="Inspect",
            tool="container_inspect",
            tool_arguments={"container_id_or_name": "private-container"},
            risk=RiskLevel.SAFE,
            required_evidence=["runtime_metadata"],
            done_when="artifact_type:runtime_metadata",
        )],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        suggested_tools=["container_inspect"],
        plan_id="plan-replan",
        additional_evidence_need=AdditionalEvidenceNeed(
            kind="runtime_metadata",
            candidate_tools=["container_inspect"],
        ),
    )
    failure = StepExecutionResult(
        step_id="old-step",
        status=StepExecutionStatus.SKIPPED,
        error="additional_evidence_needed:container_inspect",
    )

    emit_replan_trace(events.append, plan, _snapshot(), failure)

    event = events[0]
    assert event["type"] == "replan_trace"
    assert event["phase"] == "replan"
    assert event["trigger"] == "additional_evidence_needed"
    assert event["step_count"] == 1
    assert event["additional_evidence_present"] is True
    assert "steps" not in event
    assert "plan_id" not in event
    provenance = next(item for item in events if item.get("type") == "task_loop_provenance")
    assert provenance["validator_decision"] == "approved"
    assert provenance["replanned_required_evidence_count"] == 1
    assert "private-container" not in repr(event)
    assert "secret" not in repr(event)


def test_replan_trace_rejects_structured_error_code_and_message():
    events = []
    plan = ThinkingPlan(
        intent="retry",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
    )
    failure = StepExecutionResult(
        step_id="old-step",
        status=StepExecutionStatus.FAILED,
        error="{'code': 'SECRET_SENTINEL', 'message': 'private target value'}",
    )

    emit_replan_trace(events.append, plan, _snapshot(), failure)

    assert events[0]["type"] == "replan_trace"
    assert events[0]["trigger"] == "structured_error"
    assert events[0]["failure_status"] == "failed"
    assert "private target value" not in repr(events[0])
    assert "SECRET_SENTINEL" not in repr(events[0])


def test_replan_trace_fallback_omits_raw_unstructured_error_text():
    events = []
    plan = ThinkingPlan(intent="retry", steps=[], needs_task_loop=False, risk_level=RiskLevel.SAFE)
    failure = StepExecutionResult(
        step_id="old-step",
        status=StepExecutionStatus.FAILED,
        error="private-container unreachable at 10.0.0.5",
    )

    emit_replan_trace(events.append, plan, _snapshot(), failure)

    assert events[0]["trigger"] == "step_failed:failed"
    assert "private-container" not in repr(events[0])
    assert "10.0.0.5" not in repr(events[0])


def test_replan_trace_structured_error_without_code_omits_raw_message():
    events = []
    plan = ThinkingPlan(intent="retry", steps=[], needs_task_loop=False, risk_level=RiskLevel.SAFE)
    failure = StepExecutionResult(
        step_id="old-step",
        status=StepExecutionStatus.FAILED,
        error="{'error': 'private target value'}",
    )

    emit_replan_trace(events.append, plan, _snapshot(), failure)

    assert events[0]["trigger"] == "structured_error"
    assert "private target value" not in repr(events[0])


def test_replan_trace_malformed_structured_error_omits_raw_text():
    events = []
    plan = ThinkingPlan(intent="retry", steps=[], needs_task_loop=False, risk_level=RiskLevel.SAFE)
    failure = StepExecutionResult(
        step_id="old-step", status=StepExecutionStatus.FAILED,
        error="{malformed SECRET_SENTINEL PRIVATE_TOOL_SENTINEL",
    )

    emit_replan_trace(events.append, plan, _snapshot(), failure)

    assert events[0]["trigger"] == "structured_error"
    assert "SENTINEL" not in repr(events[0])
