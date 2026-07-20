from typing import Any, Callable, Dict

from core.pipeline.public_projection import public_classifier_fields, public_verifier_fields
from core.pipeline.routing_trace import routing_trace_event
from core.thinking.contracts import AdditionalEvidenceNeed, RiskLevel, ThinkingPlan

PipelineEventSink = Callable[[Dict[str, Any]], None]


def emit_pipeline_event(event_sink: PipelineEventSink | None, payload: Dict[str, Any]) -> None:
    if not callable(event_sink) or not isinstance(payload, dict):
        return
    try:
        event_sink(payload)
    except Exception:
        return


def classifier_event(classifier_result: Any) -> Dict[str, Any]:
    return {
        "type": "classifier_result",
        **public_classifier_fields(classifier_result),
    }


def thinking_plan_event(plan: Any) -> Dict[str, Any]:
    if not isinstance(plan, ThinkingPlan):
        return {"type": "thinking_plan"}
    event = {"type": "thinking_plan"}
    if isinstance(plan.steps, list):
        event["step_count"] = len(plan.steps)
    needs_task_loop = getattr(plan, "needs_task_loop", None)
    risk_level = getattr(plan, "risk_level", None)
    evidence_need = getattr(plan, "additional_evidence_need", None)
    if type(needs_task_loop) is bool:
        event["needs_task_loop"] = needs_task_loop
    if isinstance(risk_level, RiskLevel):
        event["risk_level"] = risk_level.value
    if evidence_need is None or isinstance(evidence_need, AdditionalEvidenceNeed):
        event["additional_evidence_present"] = evidence_need is not None
    return event


def verifier_event(result: Any) -> Dict[str, Any]:
    return {
        "type": "verifier_result",
        **public_verifier_fields(result),
    }
