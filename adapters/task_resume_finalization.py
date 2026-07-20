"""Prepare detached, JSON-safe task result updates before store mutation."""
import json
from typing import Any

from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopState
from core.thinking.contracts import ThinkingPlan

from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict


def prepared_result_update(result: TaskLoopResult, *, updated_at: str) -> dict[str, Any]:
    if type(result) is not TaskLoopResult:
        raise ValueError("invalid_task_loop_result")
    update: dict[str, Any] = {
        "status": result.state.value,
        "updated_at": updated_at,
        "snapshot": snapshot_to_dict(result.snapshot),
        "result": {
            "state": result.state.value,
            "stop_reason": result.stop_reason.value if result.stop_reason else None,
            "visible_content": result.visible_content,
            "artifacts": list(result.artifacts),
        },
    }
    if type(result.active_plan) is ThinkingPlan:
        update["plan"] = plan_to_dict(result.active_plan)
        update["plan_id"] = result.active_plan.plan_id or result.snapshot.plan_id
    return _json_copy(update)


def prepared_failure_update(task: dict[str, Any], *, updated_at: str) -> dict[str, Any]:
    snapshot = task.get("snapshot")
    if type(snapshot) is not dict:
        raise ValueError("invalid_trusted_snapshot")
    blocked_snapshot = {
        **snapshot,
        "state": TaskLoopState.BLOCKED.value,
        "stop_reason": StopReason.STEP_FAILED.value,
    }
    return _json_copy({
        "status": TaskLoopState.BLOCKED.value,
        "updated_at": updated_at,
        "snapshot": blocked_snapshot,
        "result": {
            "state": TaskLoopState.BLOCKED.value,
            "stop_reason": StopReason.STEP_FAILED.value,
            "visible_content": "Task loop blocked.",
            "artifacts": [],
        },
    })


def _json_copy(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))
