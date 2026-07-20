"""Task-loop classification helpers for the fallback analyzer.

Determines how the fallback path should frame multi-step execution:
whether it looks like a loop, a narrated plan, a single tool call, or
nothing at all — plus the matching reason text, confidence, and a rough
step estimate.
"""

from __future__ import annotations

from core.classifier.contracts import Category


def task_loop_kind(category: Category | None, tools: list[str], *, requested_loop: bool) -> str:
    if requested_loop and tools:
        return "loop"
    if tools:
        return "visible_multistep" if len(tools) > 1 else "single_tool"
    if category == Category.PLANNING:
        return "narrated_plan"
    return "none"


def task_loop_reason(category: Category | None, tools: list[str], *, requested_loop: bool) -> str:
    if requested_loop and tools:
        return "User requested repeated execution with visible retries."
    if requested_loop:
        return "User requested repeated execution, but no executable tools were resolved."
    if tools:
        return "Tools required for execution."
    if category == Category.TOOL:
        return "Classifier identified tool category but no executable tools resolved — answering directly with caveat."
    if category == Category.PLANNING:
        return "Planning request — answer narrates steps without tool execution."
    return "Direct answer is sufficient."


def task_loop_confidence(category: Category | None, tools: list[str], *, requested_loop: bool) -> float:
    if requested_loop and tools:
        return 0.9
    if tools:
        return 0.75
    if category == Category.PLANNING:
        return 0.4
    return 0.2


def estimated_steps(category: Category | None, tools: list[str], *, requested_loop: bool, repeat_count: int) -> int:
    if requested_loop and tools:
        return max(2, repeat_count)
    if tools:
        return max(1, len(tools))
    if category == Category.PLANNING:
        return 2
    return 1
