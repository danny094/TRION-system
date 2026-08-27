import json
from types import SimpleNamespace

from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_replan_trace, emit_task_loop_state
from core.task_loop.provenance_trace import task_loop_provenance_event
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def _snapshot(*, artifacts=None, state=TaskLoopState.EXECUTING) -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="secret user text",
        state=state,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=2,
        artifacts=list(artifacts or []),
    )


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="container check",
        steps=[
            PlanStep(
                step_id="s1",
                title="Check",
                goal="Check",
                tool="private_tool_name",
                tool_arguments={"target": "raw-target-sentinel"},
                risk=RiskLevel.SAFE,
                required_evidence=["runtime_logs", "tool_result", "SECRET_SENTINEL"],
                done_when="artifact_type:runtime_logs",
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-1",
    )


def test_provenance_event_omits_legacy_evidence_projection_and_raw_values():
    event = task_loop_provenance_event(
        _snapshot(
            artifacts=[
                {
                    "artifact_type": "tool_result",
                    "content": "USER_TEXT_SENTINEL raw-target-sentinel ARG_SENTINEL SECRET_SENTINEL",
                },
                {
                    "artifact_type": "runtime_logs",
                    "content": {"dump": "ARTIFACT_SECRET"},
                    "metadata": {
                        "validated_evidence": True,
                        "operation_contract_fingerprint": "fp-secret",
                    },
                },
            ]
        )
    )
    serialized = json.dumps(event, ensure_ascii=False)

    assert "evidence_present" not in event
    assert "validated_evidence_count" not in event
    assert "validated_evidence_types" not in event
    assert "generic_tool_result_count" not in event
    assert "artifact_count" not in event
    assert "USER_TEXT_SENTINEL" not in serialized
    assert "raw-target-sentinel" not in serialized
    assert "ARG_SENTINEL" not in serialized
    assert "ARTIFACT_SECRET" not in serialized
    assert "SECRET_SENTINEL" not in serialized


def test_missing_context_fails_closed_without_fallback_truth():
    event = task_loop_provenance_event(_snapshot())

    assert "evidence_present" not in event
    assert "validated_evidence_count" not in event
    assert "validated_evidence_types" not in event
    assert event["transition_present"] is False
    assert event["replan_proposed"] is False
    assert event["validator_decision"] == ""


def test_transition_replan_and_validator_decision_are_sanitized():
    snapshot = _snapshot().transition_to(TaskLoopState.REFLECTING).transition_to(TaskLoopState.REPLANNING)
    failure = StepExecutionResult(
        step_id="s1",
        status=StepExecutionStatus.SKIPPED,
        error="additional_evidence_needed:runtime_logs",
    )
    event = task_loop_provenance_event(
        snapshot,
        phase="replan",
        plan=_plan(),
        failure=failure,
        validator_decision="approved",
    )
    serialized = json.dumps(event, ensure_ascii=False)

    assert event["transition_present"] is True
    assert event["transition_from"] == "reflecting"
    assert event["transition_to"] == "replanning"
    assert event["replan_proposed"] is True
    assert event["validator_decision"] == "approved"
    assert event["replan_trigger"] == "additional_evidence_needed"
    assert event["replanned_required_evidence_present"] is True
    assert event["replanned_required_evidence_count"] == 2
    assert "private_tool_name" not in serialized
    assert "raw-target-sentinel" not in serialized
    assert "SECRET_SENTINEL" not in serialized


def test_state_and_replan_emit_provenance_events():
    events: list[dict] = []
    emit_task_loop_state(events.append, _snapshot().transition_to(TaskLoopState.REFLECTING), total_steps=1)

    provenance = [event for event in events if event.get("type") == "task_loop_provenance"]
    assert provenance[0]["transition_from"] == "executing"
    assert provenance[0]["transition_to"] == "reflecting"

    replan_events: list[dict] = []
    emit_replan_trace(
        replan_events.append,
        _plan(),
        _snapshot(state=TaskLoopState.REPLANNING),
        StepExecutionResult(step_id="s1", status=StepExecutionStatus.FAILED, error="{'code': 'NEEDS_MORE'}"),
    )

    replan_provenance = [event for event in replan_events if event.get("type") == "task_loop_provenance"]
    assert replan_provenance[0]["validator_decision"] == "approved"
    assert replan_provenance[0]["replan_trigger"] == "structured_error"


def test_replan_trigger_rejects_structured_failure_codes_and_raw_text():
    for raw_error, expected in [
        ("{'code': 'SECRET_SENTINEL', 'message': 'raw-target-sentinel'}", "structured_error"),
        ("{malformed SECRET_SENTINEL", "structured_error"),
        ("private exception SECRET_SENTINEL raw-target-sentinel", "step_failed:failed"),
    ]:
        event = task_loop_provenance_event(
            _snapshot(state=TaskLoopState.REPLANNING),
            failure=StepExecutionResult(
                step_id="s1",
                status=StepExecutionStatus.FAILED,
                error=raw_error,
            ),
        )
        serialized = json.dumps(event, ensure_ascii=False)

        assert event["replan_trigger"] == expected
        assert "SECRET_SENTINEL" not in serialized
        assert "raw-target-sentinel" not in serialized
        assert "private exception" not in serialized


def test_replan_trigger_rejects_non_enum_failure_status():
    event = task_loop_provenance_event(
        _snapshot(state=TaskLoopState.REPLANNING),
        failure=SimpleNamespace(status="SECRET_SENTINEL", error=""),
    )
    serialized = json.dumps(event, ensure_ascii=False)

    assert event["replan_trigger"] == "step_failed:unknown"
    assert "SECRET_SENTINEL" not in serialized
