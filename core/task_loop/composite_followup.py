"""Neutral guards for callback-owned composite plan expansion."""
from typing import Any

from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus
from core.thinking.contracts import ThinkingPlan


def expanded_plan_after_success(
    plan: ThinkingPlan,
    predecessor_step: Any,
    result: StepExecutionResult,
    planner: Any,
) -> ThinkingPlan | None:
    if (
        type(plan) is not ThinkingPlan
        or type(result) is not StepExecutionResult
        or result.status is not StepExecutionStatus.SUCCESS
        or not callable(planner)
        or not plan.steps
        or plan.steps[-1] is not predecessor_step
    ):
        return None
    try:
        expanded = planner(plan, predecessor_step, result)
    except Exception:
        return None
    if type(expanded) is not ThinkingPlan or len(expanded.steps) != len(plan.steps) + 1:
        return None
    if expanded.steps[:-1] != plan.steps or expanded.plan_id != plan.plan_id:
        return None
    step_ids = tuple(step.step_id for step in expanded.steps)
    if any(not step_id for step_id in step_ids) or len(set(step_ids)) != len(step_ids):
        return None
    return expanded
