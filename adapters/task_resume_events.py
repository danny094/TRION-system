"""Public waiting event projection for internally persisted tasks."""
from typing import Any

from core.task_loop.contracts import TaskLoopResult
from core.task_loop.event_sanitization import public_waiting_fields


def waiting_result_event_payload(task_id: str, result: TaskLoopResult) -> dict[str, Any]:
    return {
        "type": "task_loop_waiting", "task_id": task_id,
        "state": result.state.value,
        "stop_reason": result.stop_reason.value if result.stop_reason else None,
        **public_waiting_fields(result.snapshot.waiting_reason, result.snapshot.waiting_source),
        "current_step_index": result.snapshot.current_step_index,
        "total_steps": result.snapshot.total_steps,
        "completed_count": len(result.snapshot.completed_steps),
    }
