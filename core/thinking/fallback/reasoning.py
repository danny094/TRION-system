"""Reasoning helpers for the fallback analyzer.

`reasoning_type` decides whether the fallback plan should be framed as
execution, planning, or a direct answer.
"""

from __future__ import annotations

from core.classifier.contracts import Category


def reasoning_type(category: Category | None, tools: list[str]) -> str:
    if tools:
        return "execution"
    if category == Category.PLANNING:
        return "planning"
    return "direct"
