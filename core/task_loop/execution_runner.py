from core.task_loop.approval_policy import requires_waiting
from core.task_loop.composite_followup import expanded_plan_after_success
from core.task_loop.completion_gate import finalize_completion
from core.task_loop.contracts import CompletionStatus, StepExecutionStatus, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_task_loop_state
from core.task_loop.executor import TaskLoopEventSink, ToolRunner, execute_step
from core.task_loop.presentation import completion_status_for, visible_content_for
from core.task_loop.receipt_flow import append_execution, receipt_blocked, receipt_for_step
from core.task_loop.reflection import ReflectionAction, evaluate
from core.task_loop.step_governor import start_governed_step
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.thinking.contracts import ThinkingPlan


def _execute_with_reflection(
    plan: ThinkingPlan,
    snapshot: TaskLoopSnapshot,
    tool_runner: ToolRunner,
    *,
    default_timeout_s: float = 30.0,
    event_sink: TaskLoopEventSink | None = None,
    available_evidence_types: frozenset = frozenset(),
    tool_details_by_name=None,
    operation_contract_fingerprint: str | None = None,
    step_receipts: dict[str, StepOperationReceipt] | None = None,
    receipt_issuer=None,
    receipt_validator=None,
    receipt_mode: bool = False,
    approved_step_id: str = "",
    receipt_validator_factory=None,
    followup_planner=None,
) -> tuple[TaskLoopResult, object | None, ThinkingPlan]:
    total_steps = len(plan.steps)
    structural_results: tuple[object | None, ...] = ()
    if total_steps == 0:
        completed = snapshot.transition_to(TaskLoopState.COMPLETED, pending_step="", stop_reason=None)
        emit_task_loop_state(event_sink, completed, total_steps=0)
        return (
            TaskLoopResult(
                state=completed.state,
                stop_reason=completed.stop_reason,
                artifacts=list(completed.artifacts),
                visible_content="Task loop completed.",
                snapshot=completed,
                completion_status=CompletionStatus.COMPLETE,
            ),
            None,
            plan,
        )
    working = snapshot
    completion_kwargs = {"total_steps": total_steps, "event_sink": event_sink, "available_evidence_types": available_evidence_types, "expected_operation_contract_fingerprint": operation_contract_fingerprint}
    while working.current_step_index < total_steps:
        step = plan.steps[working.current_step_index]
        receipt = receipt_for_step(step, plan, working, step_receipts, receipt_issuer, receipt_validator)
        receipt_protocol_active = receipt_mode is True or step_receipts is not None or bool(working.step_operation_executions) or callable(receipt_issuer) or callable(receipt_validator)
        if receipt_protocol_active and receipt is None:
            blocked, failed = receipt_blocked(working, step, total_steps, event_sink, structural_results)
            return blocked, failed, plan
        waiting_gate = None if step.step_id == approved_step_id else requires_waiting(step, working)
        if waiting_gate is not None:
            stop_reason, waiting_reason, waiting_source = waiting_gate
            waiting = working.transition_to(
                TaskLoopState.WAITING,
                pending_step=step.step_id,
                stop_reason=stop_reason,
                waiting_reason=waiting_reason,
                waiting_source=waiting_source,
            )
            emit_task_loop_state(event_sink, waiting, step_id=step.step_id, step_title=step.title, total_steps=total_steps)
            return (
                TaskLoopResult(
                    state=waiting.state,
                    stop_reason=waiting.stop_reason,
                    artifacts=list(waiting.artifacts),
                    visible_content=f"Approval required before step '{step.title}' can run.",
                    snapshot=waiting,
                    completion_status=CompletionStatus.WAITING,
                    structural_results=structural_results,
                ),
                None,
                plan,
            )
        gate = start_governed_step(
            working, step_id=step.step_id, step_title=step.title, total_steps=total_steps,
            event_sink=event_sink, structural_results=structural_results,
        )
        if gate.blocked is not None:
            return gate.blocked, None, plan
        working = gate.snapshot
        emit_task_loop_state(event_sink, working, step_id=step.step_id, step_title=step.title, total_steps=total_steps)
        result = execute_step(step, tool_runner, artifacts=list(working.artifacts), default_timeout_s=default_timeout_s,
                              event_sink=event_sink, tool_details_by_name=tool_details_by_name,
                              operation_contract_fingerprint=operation_contract_fingerprint, governor_snapshot=working,
                              receipt=receipt)
        reflected = working.transition_to(TaskLoopState.REFLECTING)
        if result.status is StepExecutionStatus.SUCCESS:
            structural_results = (*structural_results, result.structural_result)
        decision = evaluate(result, reflected, total_steps=total_steps)
        artifacts = [*reflected.artifacts, *result.artifacts]
        error_count = reflected.error_count + (0 if result.status == StepExecutionStatus.SUCCESS else 1)
        updates = {
            "artifacts": artifacts,
            "retry_counts": decision.retry_counts,
            "progress_signature": decision.progress_signature,
            "no_progress_count": decision.no_progress_count,
            "error_count": error_count,
            "tool_calls": reflected.tool_calls + (1 if result.tool_call_started else 0),
            "step_operation_executions": append_execution(reflected, result),
        }
        expanded = expanded_plan_after_success(plan, step, result, followup_planner)
        if expanded is not None:
            plan = expanded
            total_steps = len(plan.steps)
            completion_kwargs["total_steps"] = total_steps
            if callable(receipt_validator_factory):
                receipt_validator = receipt_validator_factory(plan)
            working = reflected.transition_to(
                TaskLoopState.EXECUTING,
                current_step_index=reflected.current_step_index + 1,
                completed_steps=_append_completed(reflected, step.step_id),
                pending_step="",
                **updates,
            )
            emit_task_loop_state(
                event_sink, working, step_id=step.step_id, step_title=step.title, total_steps=total_steps,
            )
            continue
        if decision.action == ReflectionAction.CONTINUE and result.status == StepExecutionStatus.SUCCESS:
            working = reflected.transition_to(TaskLoopState.EXECUTING, current_step_index=reflected.current_step_index + 1,
                                               completed_steps=_append_completed(reflected, step.step_id), pending_step="", **updates)
            emit_task_loop_state(event_sink, working, step_id=step.step_id, step_title=step.title, total_steps=total_steps)
            continue
        if decision.action == ReflectionAction.CONTINUE:
            working = reflected.transition_to(TaskLoopState.EXECUTING, pending_step=step.step_id, **updates)
            emit_task_loop_state(event_sink, working, step_id=step.step_id, step_title=step.title, total_steps=total_steps)
            continue

        target_state = {
            ReflectionAction.WAITING: TaskLoopState.WAITING,
            ReflectionAction.REPLAN: TaskLoopState.REPLANNING,
            ReflectionAction.BLOCK: TaskLoopState.BLOCKED,
        }.get(decision.action, TaskLoopState.COMPLETED)
        final_snapshot = reflected.transition_to(
            target_state, current_step_index=reflected.current_step_index + (1 if decision.action == ReflectionAction.COMPLETED else 0),
            replan_count=reflected.replan_count + (1 if decision.action == ReflectionAction.REPLAN else 0),
            completed_steps=_append_completed(reflected, step.step_id) if decision.action == ReflectionAction.COMPLETED else list(reflected.completed_steps),
            pending_step="" if decision.action == ReflectionAction.COMPLETED else step.step_id, stop_reason=decision.stop_reason,
            waiting_reason=decision.waiting_reason, waiting_source=decision.waiting_source, **updates)
        if decision.action == ReflectionAction.COMPLETED:
            completed, failed = finalize_completion(
                plan, final_snapshot, structural_results=structural_results, **completion_kwargs,
            )
            return completed, failed, plan
        emit_task_loop_state(event_sink, final_snapshot, step_id=step.step_id, step_title=step.title, total_steps=total_steps)
        return (
            TaskLoopResult(
                state=final_snapshot.state,
                stop_reason=final_snapshot.stop_reason,
                artifacts=list(final_snapshot.artifacts),
                visible_content=visible_content_for(final_snapshot.state, step.title, final_snapshot.stop_reason),
                snapshot=final_snapshot,
                completion_status=completion_status_for(final_snapshot.state),
                structural_results=structural_results,
            ),
            result,
            plan,
        )
    completed = working.transition_to(TaskLoopState.COMPLETED, pending_step="", stop_reason=None)
    result, failed = finalize_completion(
        plan, completed, structural_results=structural_results, **completion_kwargs,
    )
    return result, failed, plan


def _append_completed(snapshot: TaskLoopSnapshot, step_id: str) -> list[str]:
    if step_id in snapshot.completed_steps:
        return list(snapshot.completed_steps)
    return [*snapshot.completed_steps, step_id]
