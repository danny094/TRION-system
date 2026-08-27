"""TaskLoop replan transport; semantic validation remains callback-owned."""
from dataclasses import replace
from typing import Any

from core.task_loop.contracts import StepExecutionResult, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_replan_trace, emit_task_loop_state
from core.task_loop.replan_contract_block import blocked_replan_result
from core.task_loop.runner import run_task_loop_with_outcome
from core.thinking.contracts import PlanContractViolation, ThinkingPlan


def run_with_replanning(
    plan: ThinkingPlan, snapshot: TaskLoopSnapshot, tool_runner: Any, *, replanner_fn: Any,
    default_timeout_s: float = 30.0, event_sink: Any = None,
    available_evidence_types: frozenset = frozenset(), tool_details_by_name: Any = None,
    operation_contract_fingerprint: str | None = None, step_receipts: dict | None = None,
    receipt_issuer: Any = None, receipt_validator: Any = None,
    receipt_validator_factory: Any = None, receipt_mode: bool = False,
    approved_step_id: str = "", followup_planner: Any = None,
) -> TaskLoopResult:
    active_plan, active_snapshot = plan, snapshot
    active_receipts, active_validator = step_receipts, receipt_validator
    while True:
        result, failed = run_task_loop_with_outcome(
            active_plan, active_snapshot, tool_runner,
            default_timeout_s=default_timeout_s, event_sink=event_sink,
            available_evidence_types=available_evidence_types,
            tool_details_by_name=tool_details_by_name,
            operation_contract_fingerprint=operation_contract_fingerprint,
            step_receipts=active_receipts, receipt_issuer=receipt_issuer,
            receipt_validator=active_validator, receipt_mode=receipt_mode,
            approved_step_id=approved_step_id,
            receipt_validator_factory=receipt_validator_factory,
            followup_planner=followup_planner,
        )
        if type(result.active_plan) is ThinkingPlan:
            active_plan = result.active_plan
        approved_step_id = ""
        if result.state != TaskLoopState.REPLANNING or not callable(replanner_fn):
            return replace(result, active_plan=active_plan)
        if not isinstance(failed, StepExecutionResult):
            return replace(result, active_plan=active_plan)
        try:
            replanned = replanner_fn(
                active_plan, objective=result.snapshot.objective,
                failed_step_id=result.snapshot.pending_step, failure=failed,
                snapshot=result.snapshot,
            )
        except PlanContractViolation as exc:
            blocked = blocked_replan_result(
                result.snapshot, event_sink, str(exc), len(active_plan.steps), result.structural_results,
            )
            return replace(blocked, active_plan=active_plan)
        emit_replan_trace(event_sink, replanned, result.snapshot, failed)
        if not replanned.needs_task_loop:
            completed = result.snapshot.transition_to(
                TaskLoopState.COMPLETED, plan_id=replanned.plan_id or result.snapshot.plan_id,
                current_step_index=0, completed_steps=[], step_operation_executions=[],
                pending_step="", stop_reason=None, waiting_reason=None, waiting_source=None,
                retry_counts={}, progress_signature="", no_progress_count=0,
            )
            emit_task_loop_state(event_sink, completed, step_title="replanned_to_answer", total_steps=len(replanned.steps))
            return TaskLoopResult(
                completed.state, completed.stop_reason, list(completed.artifacts),
                "Task loop completed.", completed, active_plan=replanned,
            )
        epoch = reset_for_replanned_plan(result.snapshot, replanned)
        active_plan, active_snapshot = replanned, epoch
        active_receipts = {} if receipt_mode else None
        active_validator = receipt_validator_factory(replanned) if receipt_mode and callable(receipt_validator_factory) else None
        emit_task_loop_state(event_sink, active_snapshot, step_title="replanned", total_steps=len(active_plan.steps))


def reset_for_replanned_plan(snapshot: TaskLoopSnapshot, plan: ThinkingPlan) -> TaskLoopSnapshot:
    return snapshot.transition_to(
        TaskLoopState.EXECUTING, plan_id=plan.plan_id or snapshot.plan_id,
        current_step_index=0, completed_steps=[], step_operation_executions=[],
        pending_step="", stop_reason=None, waiting_reason=None, waiting_source=None,
        retry_counts={}, progress_signature="", no_progress_count=0,
    )
