"""TaskLoop transport for validator-issued operation receipts."""
from core.task_loop.contracts import StepOperationExecution, StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_task_loop_state
from core.task_loop.presentation import completion_status_for, visible_content_for
from core.task_loop.step_operation_receipt import (
    ReceiptIssuer, ReceiptValidationContext, ReceiptValidator, StepOperationReceipt,
)


def receipt_for_step(
    step, plan, snapshot: TaskLoopSnapshot, receipts, issuer: ReceiptIssuer | None,
    validator: ReceiptValidator | None,
) -> StepOperationReceipt | None:
    receipt = (receipts or {}).get(step.step_id)
    if receipt is None and callable(issuer):
        try:
            receipt = issuer(step, latest_execution(snapshot))
        except Exception:
            return None
    if not isinstance(receipt, StepOperationReceipt) or not callable(validator):
        return None
    try:
        context = ReceiptValidationContext(
            plan_step_ids=tuple(getattr(item, "step_id", None) for item in getattr(plan, "steps", ())),
            current_step_index=snapshot.current_step_index,
            completed_steps=tuple(snapshot.completed_steps),
            executions=tuple(snapshot.step_operation_executions),
            current_step_id=getattr(step, "step_id", None),
        )
        validated = validator(step, receipt, context)
        return validated if type(validated) is StepOperationReceipt else None
    except Exception:
        return None


def append_execution(snapshot: TaskLoopSnapshot, result) -> list[StepOperationExecution]:
    if result.receipt is None:
        return list(snapshot.step_operation_executions)
    return [*snapshot.step_operation_executions, StepOperationExecution(result.receipt, result.status)]


def latest_execution(snapshot: TaskLoopSnapshot) -> StepOperationExecution | None:
    return snapshot.step_operation_executions[-1] if snapshot.step_operation_executions else None


def receipt_blocked(snapshot, step, total_steps, event_sink):
    blocked = snapshot.transition_to(TaskLoopState.BLOCKED, pending_step=step.step_id,
                                     stop_reason=StopReason.CAPABILITY_GAP,
                                     waiting_reason="step_operation_receipt_missing",
                                     waiting_source="plan_contract_validator")
    emit_task_loop_state(event_sink, blocked, step_id=step.step_id, step_title=step.title, total_steps=total_steps)
    return TaskLoopResult(blocked.state, blocked.stop_reason, list(blocked.artifacts),
                          visible_content_for(blocked.state, step.title, blocked.stop_reason), blocked,
                          completion_status_for(blocked.state)), None
