from typing import Any

from core.pipeline.common import contract_dict
from core.task_loop.contracts import TaskLoopSnapshot
from core.thinking.contracts import ThinkingPlan
from adapters.task_resume_schema import parse_plan, parse_snapshot


def plan_to_dict(plan: ThinkingPlan) -> dict[str, Any]:
    return contract_dict(plan)


def snapshot_to_dict(snapshot: TaskLoopSnapshot) -> dict[str, Any]:
    return contract_dict(snapshot)


def plan_from_dict(data: Any) -> ThinkingPlan:
    return parse_plan(data)


def snapshot_from_dict(data: dict[str, Any]) -> TaskLoopSnapshot:
    return parse_snapshot(data)
