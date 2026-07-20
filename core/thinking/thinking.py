from typing import Any, Mapping

from core.classifier.contracts import ClassifierResult
from core.input_processor.contracts import DocumentContext
from core.thinking.analyzer import analyze_request
from core.thinking.contracts import ThinkingPlan
from core.thinking.planner import build_plan_from_analysis


def build_plan(
    user_text: str,
    classifier_result: ClassifierResult,
    orchestrator_context: Mapping[str, Any] | None = None,
    document_context: DocumentContext | None = None,
) -> ThinkingPlan:
    available_tools = list(
        (orchestrator_context or {}).get("available_tool_details")
        or (orchestrator_context or {}).get("available_tools")
        or []
    )
    selected_tools = list(
        (orchestrator_context or {}).get("selected_tool_details")
        or (orchestrator_context or {}).get("selected_tools")
        or []
    )
    context_block = (orchestrator_context or {}).get("context")
    raw_plan = analyze_request(
        user_text,
        classifier_result,
        available_tools=available_tools,
        selected_tools=selected_tools,
        orchestrator_context=context_block if isinstance(context_block, Mapping) else None,
        document_context=document_context,
    )
    plan = build_plan_from_analysis(
        raw_plan,
        user_text=user_text,
        classifier_result=classifier_result,
        document_context=document_context,
        orchestrator_context=dict(orchestrator_context or {}),
    )
    if plan.reasoning:
        return plan
    return ThinkingPlan(
        intent=plan.intent,
        steps=plan.steps,
        needs_task_loop=plan.needs_task_loop,
        risk_level=plan.risk_level,
        reasoning=f"Route {classifier_result.route.value} produced a planning result.",
        suggested_tools=plan.suggested_tools,
        context_hints=plan.context_hints,
        plan_id=plan.plan_id,
        response_projection=plan.response_projection,
        response_derivation=plan.response_derivation,
        additional_evidence_need=plan.additional_evidence_need,
    )
