"""Entry-Point für core.thinking.planner.

Öffentliche API: build_plan_from_analysis.
Alle Logik liegt in den Submodulen; dieser Entry-Point verdrahtet sie nur.
"""
from __future__ import annotations

from typing import Any, Dict

from core.classifier.contracts import ClassifierResult
from core.input_processor.contracts import DocumentContext
from core.thinking.contracts import ThinkingPlan
from core.thinking.planner.frame_reader import needs_loop, repeat_count, routing_frame
from core.thinking.planner.plan_meta import (
    additional_evidence_need,
    plan_id,
    response_derivation,
    response_projection,
    risk_level,
)
from core.thinking.planner.step_builder import build_steps
from core.thinking.planner.tool_resolver import resolved_suggested_tools

__all__ = ["build_plan_from_analysis"]


def build_plan_from_analysis(
    raw_plan: Dict[str, Any],
    *,
    user_text: str,
    classifier_result: ClassifierResult | None = None,
    document_context: DocumentContext | None = None,
    orchestrator_context: Dict[str, Any] | None = None,
) -> ThinkingPlan:
    suggested_tools = resolved_suggested_tools(raw_plan, orchestrator_context)
    steps = build_steps(raw_plan, user_text, suggested_tools, document_context, orchestrator_context)
    loop = needs_loop(raw_plan, orchestrator_context)
    needs_task_loop = bool(suggested_tools) and bool(steps) and any(step.tool for step in steps)
    intent = str(raw_plan.get("intent") or "answer_user").strip() or "answer_user"
    if not suggested_tools:
        intent = "answer_user"
    frame = routing_frame(orchestrator_context)
    evidence_need = additional_evidence_need(raw_plan)
    if evidence_need is not None and evidence_need.candidate_tools and all(
        tool in suggested_tools for tool in evidence_need.candidate_tools
    ):
        # Plan deckt die fehlende Evidence bereits ab (Tool ist jetzt eingeplant) —
        # Bedarf ist fuer diesen Plan erledigt, kein veralteter Hinweis mehr.
        evidence_need = None
    return ThinkingPlan(
        intent=intent,
        steps=steps,
        needs_task_loop=needs_task_loop,
        risk_level=risk_level(raw_plan),
        reasoning=str(raw_plan.get("reasoning") or "").strip(),
        suggested_tools=suggested_tools,
        context_hints={
            "user_text": user_text,
            "needs_memory": bool(raw_plan.get("needs_memory", False)),
            "memory_keys": list(raw_plan.get("memory_keys") or []),
            "needs_chat_history": bool(raw_plan.get("needs_chat_history", False)),
            "response_tone": str(raw_plan.get("response_tone") or "mirror_user"),
            "response_length_hint": str(raw_plan.get("response_length_hint") or "short"),
            "dialogue_act": str(raw_plan.get("dialogue_act") or "request"),
            "tone_confidence": float(raw_plan.get("tone_confidence") or 0.0),
            "suggested_response_style": str(raw_plan.get("suggested_response_style") or "kurz"),
            "task_loop_reason": str(raw_plan.get("task_loop_reason") or ""),
            "task_loop_kind": str(raw_plan.get("task_loop_kind") or ""),
            "task_loop_confidence": float(raw_plan.get("task_loop_confidence") or 0.0),
            "estimated_steps": int(raw_plan.get("estimated_steps") or len(steps) or 1),
            "needs_loop": loop,
            "repeat_count_hint": repeat_count(raw_plan, frame),
            "routing_execution_mode": str(frame.get("execution_mode") or ""),
            "reasoning_type": str(raw_plan.get("reasoning_type") or "direct"),
            "classifier_route": classifier_result.route.value if classifier_result else "",
            "document_retrieval_mode": str(raw_plan.get("document_retrieval_mode") or "none"),
            "needs_visible_progress": bool(raw_plan.get("needs_visible_progress", False)),
        },
        plan_id=plan_id(raw_plan, suggested_tools),
        response_projection=response_projection(raw_plan),
        response_derivation=response_derivation(raw_plan),
        additional_evidence_need=evidence_need,
    )
