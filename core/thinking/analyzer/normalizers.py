"""Normalisiert raw_plan-Dicts nach LLM-Aufruf oder Fallback.

Drei Transformationen, jede zustandslos: Eingabe-Dict → neues Dict.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from core.thinking.analyzer.helpers import natural_repeat_count, routing_frame, tool_names
from utils.time_followups import has_derivable_time_followup


def normalize_derivable_time_followup(
    raw_plan: Dict[str, Any],
    user_text: str,
    orchestrator_context: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    if not has_derivable_time_followup(user_text, orchestrator_context):
        return raw_plan
    suggested_tools = tool_names(raw_plan.get("suggested_tools"))
    if any(tool != "time_now" for tool in suggested_tools):
        return raw_plan
    normalized = dict(raw_plan)
    normalized["suggested_tools"] = []
    normalized["task_loop_candidate"] = False
    normalized["task_loop_kind"] = "none"
    normalized["reasoning_type"] = str(normalized.get("reasoning_type") or "direct")
    reasoning = str(normalized.get("reasoning") or "").strip()
    suffix = "Existing grounded time evidence is sufficient for this follow-up."
    normalized["reasoning"] = f"{reasoning} {suffix}".strip() if reasoning else suffix
    return normalized


def normalize_loop_hints(
    raw_plan: Dict[str, Any],
    *,
    user_text: str,
    orchestrator_context: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    normalized = dict(raw_plan)
    frame = routing_frame(orchestrator_context)
    routing_execution_mode = str(frame.get("execution_mode") or "").strip()
    signals = frame.get("source_signals") if isinstance(frame, Mapping) else None
    routing_repeat = 1
    if isinstance(signals, Mapping):
        try:
            routing_repeat = max(1, int(signals.get("repeat_count") or 1))
        except (TypeError, ValueError):
            routing_repeat = 1
    llm_needs_loop = bool(normalized.get("needs_loop"))
    task_loop_candidate = bool(normalized.get("task_loop_candidate"))
    task_loop_kind = str(normalized.get("task_loop_kind") or "").strip()
    needs_loop = llm_needs_loop or routing_execution_mode == "loop" or task_loop_kind == "loop"
    if not needs_loop and task_loop_candidate and task_loop_kind == "visible_multistep":
        needs_loop = False
    repeat_hint = normalized.get("repeat_count_hint")
    try:
        repeat_count = max(1, int(repeat_hint or 0))
    except (TypeError, ValueError):
        repeat_count = 0
    if repeat_count <= 1 and routing_repeat > 1:
        repeat_count = routing_repeat
    if repeat_count <= 1 and needs_loop:
        repeat_count = natural_repeat_count(user_text)
    if repeat_count <= 0:
        repeat_count = 1
    normalized["needs_loop"] = bool(needs_loop)
    normalized["repeat_count_hint"] = repeat_count
    if needs_loop:
        normalized["task_loop_candidate"] = True
        normalized["task_loop_kind"] = "loop"
        normalized["estimated_steps"] = max(int(normalized.get("estimated_steps") or 0), repeat_count)
    elif "task_loop_candidate" not in normalized:
        normalized["task_loop_candidate"] = False
    normalized["operation_family_hint"] = str(normalized.get("operation_family_hint") or "").strip().lower()
    return normalized


def merge_selected_tools(
    raw_plan: Dict[str, Any],
    selected_tools: Iterable[Any] | None,
    *,
    user_text: str = "",
    orchestrator_context: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    resolved_tools = tool_names(selected_tools)
    if has_derivable_time_followup(user_text, orchestrator_context):
        return normalize_derivable_time_followup(raw_plan, user_text, orchestrator_context)
    # P11 SP3-H: ein vorhandenes routing_frame heisst, die Orchestrator-/
    # Eligibility-Pipeline ist gelaufen (siehe core/thinking/fallback/tools.py).
    # Nur dann ist ein leeres selected_tools eine gueltige, gegatete
    # Tool-Ausfuehrungswahrheit, gegen die ein vom LLM trotzdem zurueck-
    # gegebenes suggested_tools (Halluzination ueber das Prompt-Menue
    # hinaus) verworfen werden muss (Schatten-Autoritaet). Ohne routing_frame
    # (kein Orchestrator-Pfad ueberhaupt) bleibt das LLM-eigene Ergebnis
    # unveraendert durchgereicht — kein neuer Heuristik-Pfad, nur Normalisierung.
    has_routing_frame = isinstance(orchestrator_context, Mapping) and isinstance(
        orchestrator_context.get("routing_frame"), Mapping
    )
    if not resolved_tools:
        if has_routing_frame and tool_names(raw_plan.get("suggested_tools")):
            cleared = dict(raw_plan)
            cleared["suggested_tools"] = []
            return cleared
        return raw_plan
    if tool_names(raw_plan.get("suggested_tools")):
        return raw_plan
    merged = dict(raw_plan)
    merged["suggested_tools"] = resolved_tools
    merged["task_loop_candidate"] = True
    if bool(merged.get("needs_loop")):
        merged["task_loop_kind"] = "loop"
    else:
        merged["task_loop_kind"] = (
            "visible_multistep" if len(resolved_tools) > 1 else "single_tool"
        )
    merged["reasoning_type"] = str(merged.get("reasoning_type") or "execution")
    reasoning = str(merged.get("reasoning") or "").strip()
    merged["reasoning"] = (
        f"{reasoning} Orchestrator selected executable tool candidates."
        if reasoning
        else "Orchestrator selected executable tool candidates."
    )
    return merged
