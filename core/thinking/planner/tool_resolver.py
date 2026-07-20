"""Bestimmt welche Tools der Plan verwenden soll.

Liest raw_plan und orchestrator_context; kein Step-Building, keine Metadaten.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable

from core.thinking.planner.frame_reader import needs_loop


def tool_list(raw_tools: Any) -> list[str]:
    if not isinstance(raw_tools, Iterable) or isinstance(raw_tools, (str, bytes, dict)):
        return []
    tools: list[str] = []
    for item in raw_tools:
        name = str(item or "").strip()
        if name and name not in tools:
            tools.append(name)
    return tools


def tool_detail_names(raw_tools: Any) -> list[str]:
    if not isinstance(raw_tools, Iterable) or isinstance(raw_tools, (str, bytes, dict)):
        return []
    tools: list[str] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name and name not in tools:
            tools.append(name)
    return tools


def should_backfill_selected_tools(
    raw_plan: Dict[str, Any], orchestrator_context: Dict[str, Any] | None
) -> bool:
    selected_details = (
        (orchestrator_context or {}).get("selected_tool_details")
        if isinstance(orchestrator_context, dict)
        else None
    )
    selected_names = tool_detail_names(selected_details)
    if not selected_names:
        selected_names = tool_list(
            (orchestrator_context or {}).get("selected_tools")
            if isinstance(orchestrator_context, dict)
            else None
        )
    if len(selected_names) != 1:
        return False
    if needs_loop(raw_plan, orchestrator_context):
        return True
    if str(raw_plan.get("task_loop_kind") or "").strip() == "loop":
        return True
    try:
        if int(raw_plan.get("repeat_count_hint") or 0) > 1:
            return True
    except (TypeError, ValueError):
        return False
    return False


def candidate_tools_from_evidence_need(raw_plan: Dict[str, Any]) -> list[str]:
    """Fallback: additional_evidence_needed.candidate_tools, wenn suggested_tools leer ist.

    Liest nur, was der Analyzer bereits aus den (gefilterten) verfuegbaren Tools
    ermittelt hat — keine neue Tool-Auswahl, kein Hardcoding (Doc 36 Regel 2).
    """
    need = raw_plan.get("additional_evidence_needed")
    if not isinstance(need, dict):
        return []
    return tool_list(need.get("candidate_tools"))


def resolved_suggested_tools(
    raw_plan: Dict[str, Any], orchestrator_context: Dict[str, Any] | None
) -> list[str]:
    suggested = tool_list(raw_plan.get("suggested_tools"))
    if suggested:
        return suggested
    evidence_tools = candidate_tools_from_evidence_need(raw_plan)
    if evidence_tools:
        return evidence_tools
    if not should_backfill_selected_tools(raw_plan, orchestrator_context):
        return []
    selected_details = (
        (orchestrator_context or {}).get("selected_tool_details")
        if isinstance(orchestrator_context, dict)
        else None
    )
    backfilled = tool_detail_names(selected_details)
    if backfilled:
        return backfilled
    selected_names = (
        (orchestrator_context or {}).get("selected_tools")
        if isinstance(orchestrator_context, dict)
        else None
    )
    return tool_list(selected_names)
