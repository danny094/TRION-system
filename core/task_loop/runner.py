from dataclasses import replace

from core.task_loop import execution_runner
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot
from core.task_loop.executor import TaskLoopEventSink, ToolRunner
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.thinking.contracts import ThinkingPlan


def run_task_loop(
    plan: ThinkingPlan,
    snapshot: TaskLoopSnapshot,
    tool_runner: ToolRunner,
    *,
    default_timeout_s: float = 30.0,
    event_sink: TaskLoopEventSink | None = None,
    tool_details_by_name=None,
    operation_contract_fingerprint: str | None = None,
    step_receipts: dict[str, StepOperationReceipt] | None = None,
    receipt_issuer=None,
    receipt_validator=None,
    receipt_mode: bool = False,
    approved_step_id: str = "",
    receipt_validator_factory=None,
    followup_planner=None,
) -> TaskLoopResult:
    result, _, active_plan = execution_runner._execute_with_reflection(
        plan,
        snapshot,
        tool_runner,
        default_timeout_s=default_timeout_s,
        event_sink=event_sink,
        tool_details_by_name=tool_details_by_name,
        operation_contract_fingerprint=operation_contract_fingerprint,
        step_receipts=step_receipts,
        receipt_issuer=receipt_issuer,
        receipt_validator=receipt_validator,
        receipt_mode=receipt_mode,
        approved_step_id=approved_step_id,
        receipt_validator_factory=receipt_validator_factory,
        followup_planner=followup_planner,
    )
    return replace(result, active_plan=active_plan)


def run_task_loop_with_outcome(
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
):
    result, failed, active_plan = execution_runner._execute_with_reflection(
        plan,
        snapshot,
        tool_runner,
        default_timeout_s=default_timeout_s,
        event_sink=event_sink,
        available_evidence_types=available_evidence_types,
        tool_details_by_name=tool_details_by_name,
        operation_contract_fingerprint=operation_contract_fingerprint,
        step_receipts=step_receipts,
        receipt_issuer=receipt_issuer,
        receipt_validator=receipt_validator,
        receipt_mode=receipt_mode,
        approved_step_id=approved_step_id,
        receipt_validator_factory=receipt_validator_factory,
        followup_planner=followup_planner,
    )
    return replace(result, active_plan=active_plan), failed
