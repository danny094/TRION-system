"""Liest Werte aus orchestrator_context und routing_frame.

Keine Tool-Logik, keine Step-Logik — nur Kontext-Zugriff.
"""
from __future__ import annotations

from typing import Any, Dict


def routing_frame(orchestrator_context: Dict[str, Any] | None) -> Dict[str, Any]:
    context = orchestrator_context or {}
    direct = context.get("routing_frame")
    if isinstance(direct, dict):
        return dict(direct)
    inner = context.get("context")
    if isinstance(inner, dict) and isinstance(inner.get("routing_frame"), dict):
        return dict(inner.get("routing_frame") or {})
    return {}


def needs_loop(raw_plan: Dict[str, Any], orchestrator_context: Dict[str, Any] | None) -> bool:
    if bool(raw_plan.get("needs_loop")):
        return True
    return str(routing_frame(orchestrator_context).get("execution_mode") or "").strip() == "loop"


def repeat_count(raw_plan: Dict[str, Any], frame: Dict[str, Any]) -> int:
    try:
        hint = max(1, int(raw_plan.get("repeat_count_hint") or 1))
    except (TypeError, ValueError):
        hint = 1
    if hint > 1:
        return hint
    signals = frame.get("source_signals")
    if not isinstance(signals, dict):
        return 1
    try:
        return max(1, int(signals.get("repeat_count") or 1))
    except (TypeError, ValueError):
        return 1


def selected_tool_detail(
    tool_name: str, orchestrator_context: Dict[str, Any] | None
) -> Dict[str, Any]:
    details = (
        (orchestrator_context or {}).get("selected_tool_details")
        if isinstance(orchestrator_context, dict)
        else None
    )
    if not isinstance(details, list):
        return {}
    for item in details:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "").strip() == tool_name:
            return dict(item)
    return {}
