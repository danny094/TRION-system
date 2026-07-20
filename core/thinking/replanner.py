from typing import Any

from core.thinking.analyzer import analyze_request
from core.thinking.contracts import ThinkingPlan
from core.thinking.planner import build_plan_from_analysis


def build_replan(
    plan: ThinkingPlan,
    *,
    objective: str,
    failed_step_id: str,
    failure: Any,
    snapshot: Any,
    available_tools: Any = None,
    orchestrator_context: Any = None,
) -> ThinkingPlan:
    """Build a replanned ThinkingPlan through the same analyzer/planner path."""
    tools = available_tools if available_tools is not None else plan.suggested_tools
    raw_plan = analyze_request(
        objective,
        classifier_result=None,
        available_tools=tools,
        orchestrator_context=orchestrator_context,
        replan_context={
            "failed_step_id": failed_step_id,
            "failure_status": getattr(getattr(failure, "status", None), "value", ""),
            "failure_error": getattr(failure, "error", ""),
            "replan_count": getattr(snapshot, "replan_count", 0),
            "artifacts": list(getattr(snapshot, "artifacts", []) or []),
        },
    )
    replanned = build_plan_from_analysis(
        raw_plan,
        user_text=objective,
        classifier_result=None,
        orchestrator_context=orchestrator_context,
    )
    hints = dict(plan.context_hints)
    hints.update(replanned.context_hints)
    hints["replan"] = {
        "failed_step_id": failed_step_id,
        "error": getattr(failure, "error", ""),
        "status": getattr(getattr(failure, "status", None), "value", ""),
        "replan_count": getattr(snapshot, "replan_count", 0),
        "artifacts": list(getattr(snapshot, "artifacts", []) or []),
    }
    return ThinkingPlan(
        intent=replanned.intent,
        steps=replanned.steps,
        needs_task_loop=replanned.needs_task_loop,
        risk_level=replanned.risk_level,
        reasoning=replanned.reasoning or plan.reasoning,
        suggested_tools=replanned.suggested_tools or list(plan.suggested_tools),
        context_hints=hints,
        plan_id=replanned.plan_id or f"{plan.plan_id or 'plan'}-replan",
        response_projection=replanned.response_projection or plan.response_projection,
        response_derivation=replanned.response_derivation or plan.response_derivation,
        additional_evidence_need=replanned.additional_evidence_need,
    )
