from core.task_loop import outcome_evaluator
from core.task_loop.contracts import (
    CompletionStatus,
    EvidenceArtifact,
    StepExecutionResult,
    StepExecutionStatus,
    StopReason,
    TaskLoopResult,
    TaskLoopSnapshot,
    TaskLoopState,
)
from core.task_loop.outcome_evaluator import OutcomeAction
from core.task_loop.events import emit_task_loop_state
from core.task_loop.executor import TaskLoopEventSink
from core.task_loop.run_governor import can_replan, current_time_ts, replan_governor_from_snapshot
from core.thinking.contracts import ThinkingPlan
from utils.response_intents import unresolved_additional_evidence_tools


def finalize_completion(
    plan: ThinkingPlan,
    snapshot: TaskLoopSnapshot,
    *,
    total_steps: int,
    event_sink: TaskLoopEventSink | None = None,
    available_evidence_types: frozenset = frozenset(),
    expected_operation_contract_fingerprint: str | None = None,
) -> tuple[TaskLoopResult, StepExecutionResult | None]:
    missing_tools = unresolved_additional_evidence_tools(plan, list(snapshot.artifacts))
    completed_step_id = snapshot.completed_steps[-1] if snapshot.completed_steps else ""
    completed_step_title = _step_title(plan, completed_step_id)
    replan_decision = can_replan(replan_governor_from_snapshot(snapshot), now_ts=current_time_ts())
    if not missing_tools:
        evidence = [EvidenceArtifact.from_dict(a) for a in snapshot.artifacts]
        outcome = outcome_evaluator.evaluate(
            plan,
            evidence,
            available_evidence_types=available_evidence_types,
            replan_budget_remaining=replan_decision.allowed,
            expected_operation_contract_fingerprint=expected_operation_contract_fingerprint,
        )

        if outcome.action == OutcomeAction.COMPLETE:
            emit_task_loop_state(event_sink, snapshot, step_id=completed_step_id, step_title=completed_step_title, total_steps=total_steps)
            return (
                TaskLoopResult(
                    state=snapshot.state,
                    stop_reason=snapshot.stop_reason,
                    artifacts=list(snapshot.artifacts),
                    visible_content="Task loop completed.",
                    snapshot=snapshot,
                    completion_status=CompletionStatus.COMPLETE,
                ),
                None,
            )

        if outcome.action == OutcomeAction.REPLAN:
            replan_snap = snapshot.transition_to(
                TaskLoopState.REPLANNING,
                pending_step=completed_step_id,
                stop_reason=outcome.stop_reason or StopReason.OBJECTIVE_NOT_MET,
                replan_count=snapshot.replan_count + 1,
            )
            emit_task_loop_state(event_sink, replan_snap, step_id=completed_step_id, step_title=completed_step_title, total_steps=total_steps)
            synthetic = StepExecutionResult(
                step_id=completed_step_id,
                status=StepExecutionStatus.SKIPPED,
                error=f"objective_not_met:{outcome.stop_reason.value if outcome.stop_reason else ''}",
            )
            return (
                TaskLoopResult(
                    state=replan_snap.state,
                    stop_reason=replan_snap.stop_reason,
                    artifacts=list(replan_snap.artifacts),
                    visible_content="Objective not yet met — triggering replanning.",
                    snapshot=replan_snap,
                    completion_status=CompletionStatus.NEEDS_REPLAN,
                ),
                synthetic,
            )

        # BLOCK — kein Budget mehr oder CAPABILITY_GAP
        blocked = snapshot.transition_to(
            TaskLoopState.BLOCKED,
            pending_step=completed_step_id,
            stop_reason=outcome.stop_reason or StopReason.OBJECTIVE_NOT_MET,
        )
        emit_task_loop_state(event_sink, blocked, step_id=completed_step_id, step_title=completed_step_title, total_steps=total_steps)
        return (
            TaskLoopResult(
                state=blocked.state,
                stop_reason=blocked.stop_reason,
                artifacts=list(blocked.artifacts),
                visible_content=f"Task loop blocked: {blocked.stop_reason.value if blocked.stop_reason else 'objective_not_met'}.",
                snapshot=blocked,
                completion_status=CompletionStatus.BLOCKED,
            ),
            None,
        )
    if not replan_decision.allowed:
        blocked = snapshot.transition_to(
            TaskLoopState.BLOCKED,
            pending_step=snapshot.completed_steps[-1] if snapshot.completed_steps else "additional_evidence",
            stop_reason=StopReason.REPLAN_BUDGET_EXHAUSTED,
            waiting_reason=replan_decision.reason,
            waiting_source="run_governor",
        )
        emit_task_loop_state(
            event_sink,
            blocked,
            step_id=blocked.pending_step,
            step_title="additional_evidence_budget_exhausted",
            total_steps=total_steps,
        )
        return (
            TaskLoopResult(
                state=blocked.state,
                stop_reason=blocked.stop_reason,
                artifacts=list(blocked.artifacts),
                visible_content="Task loop stopped because the replanning budget was exhausted before additional evidence could be gathered.",
                snapshot=blocked,
                completion_status=CompletionStatus.BLOCKED,
            ),
            None,
        )
    replan_snapshot = snapshot.transition_to(
        TaskLoopState.REPLANNING,
        pending_step=snapshot.completed_steps[-1] if snapshot.completed_steps else "additional_evidence",
        stop_reason=StopReason.ADDITIONAL_EVIDENCE_REQUIRED,
        replan_count=snapshot.replan_count + 1,
    )
    emit_task_loop_state(
        event_sink,
        replan_snapshot,
        step_id=replan_snapshot.pending_step,
        step_title="replanned_for_additional_evidence",
        total_steps=total_steps,
    )
    return (
        TaskLoopResult(
            state=replan_snapshot.state,
            stop_reason=replan_snapshot.stop_reason,
            artifacts=list(replan_snapshot.artifacts),
            visible_content="Additional verified evidence is required before the objective can be completed.",
            snapshot=replan_snapshot,
            completion_status=CompletionStatus.NEEDS_MORE_EVIDENCE,
        ),
        StepExecutionResult(
            step_id=replan_snapshot.pending_step,
            status=StepExecutionStatus.SKIPPED,
            error=f"additional_evidence_needed:{','.join(missing_tools)}",
        ),
    )


def _step_title(plan: ThinkingPlan, step_id: str) -> str:
    if not step_id:
        return ""
    for step in list(getattr(plan, "steps", []) or []):
        if getattr(step, "step_id", "") == step_id:
            return getattr(step, "title", "")
    return ""
