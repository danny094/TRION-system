"""Kleine Hilfsfunktionen für den Analyzer.

Kein LLM-Aufruf, keine Normalisierung — nur Kontext-Lesen und Typ-Helfer.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping


def routing_frame(orchestrator_context: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(orchestrator_context, Mapping):
        return {}
    frame = orchestrator_context.get("routing_frame")
    return frame if isinstance(frame, Mapping) else {}


def natural_repeat_count(user_text: str) -> int:
    text = str(user_text or "").lower()
    for pattern in (
        r"\b(\d+)\s*x\b",
        r"\bf(?:u|ue)hre\s+(\d+)\b",
        r"\bmache\s+(\d+)\b",
        r"\bsuche\s+(\d+)\b",
        r"\bpr(?:ü|ue)fe\s+(\d+)\b",
    ):
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return max(1, int(match.group(1)))
        except (TypeError, ValueError):
            continue
    return 1


def tool_names(tools: Iterable[Any] | None) -> list[str]:
    names: list[str] = []
    for tool in tools or []:
        name = str(tool.get("name") if isinstance(tool, Mapping) else tool).strip()
        if name and name not in names:
            names.append(name)
    return names
