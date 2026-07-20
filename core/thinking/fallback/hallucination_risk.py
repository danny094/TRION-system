"""Hallucination-risk estimation for the fallback analyzer.

Maps the classifier category and the resolved tool list onto a coarse
risk band (high/medium/low) used to decide how cautiously the fallback
plan should be framed.
"""

from __future__ import annotations

from core.classifier.contracts import Category


def hallucination_risk(category: Category | None, tools: list[str]) -> str:
    if category == Category.RISK:
        return "high"
    if category in (Category.TOOL, Category.PLANNING) or (category == Category.UNKNOWN and tools):
        return "medium"
    return "low"
