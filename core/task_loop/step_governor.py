from dataclasses import dataclass, replace

from core.task_loop.contracts import CompletionStatus, StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_task_loop_state
from core.task_loop.presentation import visible_content_for
from core.task_loop.run_governor import can_start_step, current_time_ts, run_governor_from_snapshot


@dataclass(frozen=True)
class StepGovernorResult:
    snapshot: TaskLoopSnapshot
    blocked: TaskLoopResult | None = None


def start_governed_step(
    snapshot: TaskLoopSnapshot,
    *,
    step_id: str,
    step_title: str,
    total_steps: int,
    event_sink,
) -> StepGovernorResult:
    decision = can_start_step(run_governor_from_snapshot(snapshot), now_ts=current_time_ts())
    if not decision.allowed:
        blocked = snapshot.transition_to(
            TaskLoopState.BLOCKED,
            pending_step=step_id,
            stop_reason=StopReason.MAX_STEPS_REACHED,
            waiting_reason=decision.reason,
            waiting_source="run_governor",
        )
        emit_task_loop_state(event_sink, blocked, step_id=step_id, step_title=step_title, total_steps=total_steps)
        return StepGovernorResult(
            snapshot=blocked,
            blocked=TaskLoopResult(
                state=blocked.state,
                stop_reason=blocked.stop_reason,
                artifacts=list(blocked.artifacts),
                visible_content=visible_content_for(blocked.state, step_title, blocked.stop_reason),
                snapshot=blocked,
                completion_status=CompletionStatus.BLOCKED,
            ),
        )
    started = _mark_started(snapshot, step_id)
    return StepGovernorResult(snapshot=started)


def _mark_started(snapshot: TaskLoopSnapshot, step_id: str) -> TaskLoopSnapshot:
    updates = {
        "pending_step": step_id,
        "stop_reason": None,
        "total_steps": max(0, int(snapshot.total_steps)) + 1,
    }
    if snapshot.state == TaskLoopState.EXECUTING:
        return replace(snapshot, **updates)
    return snapshot.transition_to(TaskLoopState.EXECUTING, **updates)
