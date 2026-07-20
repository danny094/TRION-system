from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

from core.task_loop.contracts import (
    StepExecutionResult,
    StepExecutionStatus,
    StopReason,
    TaskLoopSnapshot,
)
from core.task_loop.run_governor import can_replan, current_time_ts, replan_governor_from_snapshot


class ReflectionAction(str, Enum):
    CONTINUE = "continue"
    COMPLETED = "completed"
    WAITING = "waiting"
    REPLAN = "replan"
    BLOCK = "block"


@dataclass(frozen=True)
class ReflectionDecision:
    action: ReflectionAction
    stop_reason: StopReason | None = None
    waiting_reason: str | None = None
    waiting_source: str | None = None
    retry_counts: Dict[str, int] = field(default_factory=dict)
    progress_signature: str = ""
    no_progress_count: int = 0


def _signature(result: StepExecutionResult) -> str:
    error = str(result.error or "")
    keys = ",".join(sorted(str(key) for key in result.output.keys()))
    artifact_count = len(result.artifacts)
    return f"{result.step_id}:{result.status.value}:{error}:{keys}:{artifact_count}"


def _failure_escalation(snapshot: TaskLoopSnapshot) -> str:
    raw = str(snapshot.failure_escalation or "replan").strip().lower()
    return raw if raw in {"replan", "ask", "abort"} else "replan"


def evaluate(
    result: StepExecutionResult,
    snapshot: TaskLoopSnapshot,
    *,
    total_steps: int,
) -> ReflectionDecision:
    if snapshot.current_step_index + 1 >= max(1, int(snapshot.max_steps)):
        return ReflectionDecision(ReflectionAction.BLOCK, StopReason.MAX_STEPS_REACHED)

    if result.status == StepExecutionStatus.SKIPPED:
        return ReflectionDecision(
            ReflectionAction.WAITING,
            StopReason.USER_DECISION_NEEDED,
            waiting_reason="user_decision",
            waiting_source="reflection",
        )

    next_signature = _signature(result)
    no_progress_count = snapshot.no_progress_count + 1 if next_signature == snapshot.progress_signature else 0
    threshold = max(2, int(snapshot.no_progress_threshold))
    if snapshot.loop_detection_enabled and no_progress_count >= threshold:
        return ReflectionDecision(
            ReflectionAction.BLOCK,
            StopReason.NO_PROGRESS,
            progress_signature=next_signature,
            no_progress_count=no_progress_count,
        )

    if result.status == StepExecutionStatus.SUCCESS:
        action = (
            ReflectionAction.COMPLETED
            if snapshot.current_step_index + 1 >= max(1, int(total_steps))
            else ReflectionAction.CONTINUE
        )
        return ReflectionDecision(
            action,
            progress_signature=next_signature,
            no_progress_count=no_progress_count,
        )

    retry_counts = dict(snapshot.retry_counts)
    current_retries = int(retry_counts.get(result.step_id, 0))
    if current_retries < max(0, int(snapshot.max_retries_per_step)):
        retry_counts[result.step_id] = current_retries + 1
        return ReflectionDecision(
            ReflectionAction.CONTINUE,
            retry_counts=retry_counts,
            progress_signature=next_signature,
            no_progress_count=no_progress_count,
        )

    failure_escalation = _failure_escalation(snapshot)
    if failure_escalation == "ask":
        return ReflectionDecision(
            ReflectionAction.WAITING,
            StopReason.USER_DECISION_NEEDED,
            waiting_reason="step_failed_user_decision",
            waiting_source="failure_policy",
            retry_counts=retry_counts,
            progress_signature=next_signature,
            no_progress_count=no_progress_count,
        )
    if failure_escalation == "abort":
        return ReflectionDecision(
            ReflectionAction.BLOCK,
            StopReason.FAILURE_ABORT_POLICY,
            retry_counts=retry_counts,
            progress_signature=next_signature,
            no_progress_count=no_progress_count,
        )

    replan_decision = can_replan(replan_governor_from_snapshot(snapshot), now_ts=current_time_ts())
    if not replan_decision.allowed:
        return ReflectionDecision(
            ReflectionAction.BLOCK,
            StopReason.REPLAN_BUDGET_EXHAUSTED,
            waiting_reason=replan_decision.reason,
            waiting_source="run_governor",
            retry_counts=retry_counts,
            progress_signature=next_signature,
            no_progress_count=no_progress_count,
        )

    return ReflectionDecision(
        ReflectionAction.REPLAN,
        StopReason.STEP_FAILED,
        retry_counts=retry_counts,
        progress_signature=next_signature,
        no_progress_count=no_progress_count,
    )
