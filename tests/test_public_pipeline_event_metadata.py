import json

from core.pipeline.event_stream import thinking_plan_event
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_replan_trace
from core.thinking.contracts import (
    AdditionalEvidenceNeed, PlanStep, ResponseDerivation, ResponseProjection, RiskLevel, ThinkingPlan,
)


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect",
        steps=[PlanStep(
            step_id="STEP_ID_SENTINEL", title="TITLE_SENTINEL", goal="USER_TEXT_SENTINEL",
            tool="PRIVATE_TOOL_SENTINEL", tool_arguments={"target": "TARGET_SENTINEL"},
        )],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="LLM_TEXT_SENTINEL",
        suggested_tools=["PRIVATE_TOOL_SENTINEL"],
        context_hints={"user_text": "USER_TEXT_SENTINEL"},
        plan_id="PLAN_ID_SENTINEL",
        response_projection=ResponseProjection("PROJECTION_SENTINEL"),
        response_derivation=ResponseDerivation("DERIVATION_SENTINEL"),
        additional_evidence_need=AdditionalEvidenceNeed(
            kind="runtime_metadata", reason="OUTPUT_SENTINEL",
            candidate_tools=["PRIVATE_TOOL_SENTINEL"],
        ),
    )


def test_thinking_plan_projection_contains_only_controlled_metadata():
    event = thinking_plan_event(_plan())
    serialized = json.dumps(event)

    assert event == {
        "type": "thinking_plan", "step_count": 1,
        "needs_task_loop": True, "risk_level": "safe",
        "additional_evidence_present": True,
    }
    assert "SENTINEL" not in serialized


def test_thinking_plan_projection_omits_malformed_runtime_values():
    malformed = ThinkingPlan(
        intent="INTENT_SENTINEL", steps="STEP_SENTINEL", needs_task_loop="BOOLEAN_SENTINEL",
        risk_level="RISK_SENTINEL", additional_evidence_need="EVIDENCE_SENTINEL",
    )

    assert thinking_plan_event(malformed) == {"type": "thinking_plan"}


def test_replan_projection_omits_plan_step_tool_and_artifact_values():
    snapshot = TaskLoopSnapshot(
        plan_id="PLAN_ID_SENTINEL", conversation_id="CONVERSATION_ID_SENTINEL",
        objective="USER_TEXT_SENTINEL", state=TaskLoopState.REPLANNING,
        current_step_index=0, max_steps=2, max_retries_per_step=0,
        artifacts=[{"content": "ARTIFACT_SENTINEL"}],
    )
    failure = StepExecutionResult(
        step_id="STEP_ID_SENTINEL", status=StepExecutionStatus.FAILED,
        error="additional_evidence_needed:PRIVATE_TOOL_SENTINEL",
    )
    events = []

    emit_replan_trace(events.append, _plan(), snapshot, failure)
    event = events[0]
    serialized = json.dumps(event)

    assert event["trigger"] == "additional_evidence_needed"
    assert event["step_count"] == 1
    assert event["artifact_count"] == 1
    assert "SENTINEL" not in serialized
