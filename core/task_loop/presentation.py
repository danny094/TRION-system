"""Presentation-Mapping fuer Task-Loop-Endzustaende.

Eine Aufgabe: deterministische String-/Enum-Ableitung aus bereits getroffenen
Reflection-Entscheidungen (core/task_loop/runner.py). Trifft selbst keine
Entscheidung, kein LLM-Call. Reine Verschiebung aus runner.py ohne
Verhaltensaenderung — vormals `_visible_content`/`_completion_status_for`.
"""
from __future__ import annotations

from core.task_loop.contracts import CompletionStatus, StopReason, TaskLoopState


def visible_content_for(state: TaskLoopState, step_title: str, reason: StopReason | None) -> str:
    if state == TaskLoopState.COMPLETED:
        return "Task loop completed."
    if state == TaskLoopState.WAITING:
        if reason == StopReason.RISK_GATE_REQUIRED:
            return f"Approval required before step '{step_title}' can run."
        if reason == StopReason.USER_DECISION_NEEDED:
            return f"Task loop paused after step '{step_title}' failed and needs user guidance."
        return f"Waiting for user decision on step '{step_title}'."
    if state == TaskLoopState.REPLANNING:
        return f"Step '{step_title}' failed and needs replanning."
    if reason == StopReason.FAILURE_ABORT_POLICY:
        return f"Task loop stopped at step '{step_title}' because error behavior is set to abort on failure."
    if reason == StopReason.MAX_STEPS_REACHED:
        return f"Task loop stopped at step '{step_title}' because the step budget was exhausted."
    if reason == StopReason.REPLAN_BUDGET_EXHAUSTED:
        return f"Task loop stopped at step '{step_title}' because the replanning budget was exhausted."
    if reason == StopReason.NO_PROGRESS:
        return f"Task loop stopped at step '{step_title}' because no progress was detected."
    return f"Task loop stopped at step '{step_title}'."


def completion_status_for(state: TaskLoopState) -> CompletionStatus:
    if state == TaskLoopState.REPLANNING:
        return CompletionStatus.NEEDS_REPLAN
    if state == TaskLoopState.WAITING:
        return CompletionStatus.WAITING
    if state == TaskLoopState.BLOCKED:
        return CompletionStatus.BLOCKED
    if state == TaskLoopState.CANCELLED:
        return CompletionStatus.CANCELLED
    if state == TaskLoopState.COMPLETED:
        return CompletionStatus.COMPLETE
    return CompletionStatus.INCOMPLETE
