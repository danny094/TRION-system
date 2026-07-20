"""Deterministic fallback analyzer used when the LLM analyzer is disabled.

Reads classifier signals and orchestrator context to produce a richer raw
plan than the previous keyword-only baseline. No LLM calls.

This module is the entry point only: it wires together the submodules
below and assembles their results into the raw-plan dict. The actual
decision logic (tool selection, task-loop framing, hallucination risk,
reasoning/operation framing, memory-signal detection) lives in the
sibling modules — see `core/thinking/fallback/`.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from core.classifier.contracts import Category, ClassifierResult
# C1 Bottleneck-Disziplin: Direktaufruf classify_dialogue_signal ist verboten.
# Routing läuft immer über frame_signals-Capsule (PIANO 1.0, 2026-06-11).
from core.orchestrator.frame_signals import dialogue_signal_from_frame
from core.input_processor.contracts import DocumentContext
from core.thinking.document_mode import resolve_document_retrieval_mode
from core.thinking.fallback_reasoning import build_fallback_reasoning_text
from utils.response_intents import (
    completed_tool_names,
    detect_additional_evidence_need,
    parse_response_derivation,
    parse_response_projection,
)

from core.thinking.fallback.hallucination_risk import hallucination_risk
from core.thinking.fallback.memory_signal import HISTORY_KW, MEMORY_KW, PROJECT_KW, has_memory_items
from core.thinking.fallback.reasoning import reasoning_type
from core.thinking.fallback.task_loop import (
    estimated_steps,
    task_loop_confidence,
    task_loop_kind,
    task_loop_reason,
)
from core.thinking.fallback.tools import routing_frame, suggested_tools

__all__ = ["fallback_analysis"]


def fallback_analysis(
    user_text: str,
    classifier_result: ClassifierResult | None,
    *,
    available_tools: Iterable[Any] | None,
    selected_tools: Iterable[Any] | None,
    orchestrator_context: Mapping[str, Any] | None,
    document_context: DocumentContext | None,
    replan_context: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    text = str(user_text or "").strip()
    lowered = text.lower()
    frame = routing_frame(orchestrator_context)
    dialogue_signal = dialogue_signal_from_frame(frame, text)
    requested_loop = str(frame.get("execution_mode") or "").strip() == "loop"
    repeat_count = max(1, int(frame.get("source_signals", {}).get("repeat_count") or 1)) if isinstance(frame.get("source_signals"), Mapping) else 1
    tools = suggested_tools(
        lowered,
        available_tools,
        selected_tools,
        classifier_result,
        document_context,
        orchestrator_context,
        replan_context,
    )
    retrieval_mode = resolve_document_retrieval_mode(tools, document_context, orchestrator_context, user_text=text)
    category = classifier_result.category if classifier_result else None
    has_memory = has_memory_items(orchestrator_context)
    needs_memory_kw = any(token in lowered for token in MEMORY_KW)
    needs_memory = needs_memory_kw or has_memory
    projection = parse_response_projection(text)
    derivation = parse_response_derivation(text)
    completed = completed_tool_names(
        list(replan_context.get("artifacts") or []) if isinstance(replan_context, Mapping) else []
    )
    additional_evidence = detect_additional_evidence_need(
        text,
        list(available_tools or []),
        tools,
        completed_tools=completed,
    )
    return {
        "intent": text[:120] or "answer_user",
        "suggested_tools": tools,
        "needs_memory": needs_memory,
        "memory_keys": ["project_context"] if any(token in lowered for token in PROJECT_KW) else [],
        "needs_chat_history": any(token in lowered for token in HISTORY_KW),
        "hallucination_risk": hallucination_risk(category, tools),
        "suggested_response_style": "kurz",
        "response_tone": dialogue_signal.response_tone,
        "response_length_hint": dialogue_signal.response_length_hint,
        "needs_sequential_thinking": bool(tools) or category == Category.PLANNING,
        "task_loop_candidate": bool(tools),
        "task_loop_kind": task_loop_kind(category, tools, requested_loop=requested_loop),
        "task_loop_confidence": task_loop_confidence(category, tools, requested_loop=requested_loop),
        "needs_loop": requested_loop and bool(tools),
        "repeat_count_hint": repeat_count if requested_loop else 1,
        # P11 SP7-B: keine Rohtext-Operation im Fallback rekonstruieren.
        # Downstream liest nur die vorgelagerte RoutingFrame-Projektion.
        "operation_family_hint": str(frame.get("requested_operation_family") or "").strip(),
        "estimated_steps": estimated_steps(category, tools, requested_loop=requested_loop, repeat_count=repeat_count),
        "needs_visible_progress": len(tools) > 1 or category == Category.PLANNING or requested_loop,
        "task_loop_reason": task_loop_reason(category, tools, requested_loop=requested_loop),
        "document_retrieval_mode": retrieval_mode,
        "document_chunk_ids": list(getattr(document_context, "workspace_entry_ids", []) or []),
        "document_semantic_keys": list(getattr(document_context, "semantic_keys", []) or []),
        "reasoning_type": reasoning_type(category, tools),
        "dialogue_act": dialogue_signal.dialogue_act,
        "tone_confidence": dialogue_signal.confidence,
        "reasoning": build_fallback_reasoning_text(
            classifier_result,
            tools,
            has_memory,
            projection,
            derivation,
            additional_evidence,
        ),
        "response_projection": projection,
        "response_derivation": derivation,
        "additional_evidence_needed": additional_evidence,
    }
