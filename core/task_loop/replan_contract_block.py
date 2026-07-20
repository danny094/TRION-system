from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_task_loop_state
from core.task_loop.executor import TaskLoopEventSink


def blocked_replan_result(
    snapshot: TaskLoopSnapshot,
    event_sink: TaskLoopEventSink | None,
    reason: str,
    total_steps: int,
) -> TaskLoopResult:
    blocked = snapshot.transition_to(
        TaskLoopState.BLOCKED,
        stop_reason=StopReason.CAPABILITY_GAP,
        waiting_reason=reason,
        waiting_source="plan_contract_validator",
    )
    emit_task_loop_state(
        event_sink,
        blocked,
        step_id=blocked.pending_step,
        step_title="plan_contract_blocked",
        total_steps=total_steps,
    )
    return TaskLoopResult(
        state=blocked.state,
        stop_reason=blocked.stop_reason,
        artifacts=list(blocked.artifacts),
        visible_content="Task loop blocked by plan contract validator.",
        snapshot=blocked,
    )
