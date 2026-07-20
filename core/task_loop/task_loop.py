from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.events import emit_task_loop_state
from core.task_loop.executor import TaskLoopEventSink, ToolRunner
from core.task_loop.replanning import run_with_replanning as _run_with_replanning
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.thinking.contracts import ThinkingPlan
from core.thinking.replanner import build_replan
def _resolve_objective(plan: ThinkingPlan, objective: str | None) -> str:
    if objective and objective.strip():
        return objective.strip()
    hinted = str(plan.context_hints.get("user_text", "")).strip()
    if hinted:
        return hinted
    return plan.intent
def start_task_loop(
    plan: ThinkingPlan,
    *,
    conversation_id: str,
    objective: str | None,
    tool_runner: ToolRunner,
    replanner_fn=build_replan,
    max_steps: int = 10,
    max_retries_per_step: int = 1,
    max_replans: int = 2,
    loop_detection_enabled: bool = True,
    no_progress_threshold: int = 3,
    approval_mode: str = "risk_based",
    failure_escalation: str = "replan",
    approval_required_tools: list[str] | None = None,
    default_timeout_s: float = 30.0,
    event_sink: TaskLoopEventSink | None = None,
    available_evidence_types: frozenset = frozenset(),
    tool_details_by_name=None,
    operation_contract_fingerprint: str | None = None,
    step_receipts: dict[str, StepOperationReceipt] | None = None,
    receipt_issuer=None,
    receipt_validator=None,
    receipt_validator_factory=None,
    receipt_mode: bool = False,
) -> TaskLoopResult:
    snapshot = TaskLoopSnapshot(plan_id=plan.plan_id or "task-loop", conversation_id=conversation_id,
                                objective=_resolve_objective(plan, objective), state=TaskLoopState.EXECUTING,
                                current_step_index=0, max_steps=max_steps, max_retries_per_step=max_retries_per_step,
                                max_replans=max_replans, loop_detection_enabled=loop_detection_enabled,
                                no_progress_threshold=no_progress_threshold, approval_mode=approval_mode,
                                failure_escalation=failure_escalation, approval_required_tools=list(approval_required_tools or []))
    return _run_with_replanning(
        plan,
        snapshot,
        tool_runner,
        replanner_fn=replanner_fn,
        default_timeout_s=default_timeout_s,
        event_sink=event_sink,
        available_evidence_types=available_evidence_types,
        tool_details_by_name=tool_details_by_name,
        operation_contract_fingerprint=operation_contract_fingerprint,
        step_receipts=step_receipts,
        receipt_issuer=receipt_issuer,
        receipt_validator=receipt_validator,
        receipt_validator_factory=receipt_validator_factory,
        receipt_mode=receipt_mode,
    )
def continue_task_loop(
    snapshot: TaskLoopSnapshot,
    user_text: str,
    plan: ThinkingPlan,
    *,
    tool_runner: ToolRunner,
    replanner_fn=build_replan,
    default_timeout_s: float = 30.0,
    event_sink: TaskLoopEventSink | None = None,
    tool_details_by_name=None,
    operation_contract_fingerprint: str | None = None,
    step_receipts: dict[str, StepOperationReceipt] | None = None,
    receipt_issuer=None,
    receipt_validator=None,
    receipt_validator_factory=None,
    receipt_mode: bool = False,
) -> TaskLoopResult:
    if snapshot.state != TaskLoopState.WAITING:
        raise ValueError("continue_task_loop requires a WAITING snapshot")
    normalized = user_text.strip().lower()
    if normalized in {"cancel", "stop", "abort", "abbrechen"}:
        cancelled = snapshot.transition_to(TaskLoopState.CANCELLED, stop_reason=StopReason.USER_CANCELLED,
                                           pending_step=snapshot.pending_step)
        emit_task_loop_state(event_sink, cancelled, step_id=cancelled.pending_step, step_title="cancelled", total_steps=len(plan.steps))
        return TaskLoopResult(cancelled.state, cancelled.stop_reason, list(cancelled.artifacts),
                              "Task loop cancelled by user.", cancelled)
    resumed = snapshot.transition_to(TaskLoopState.EXECUTING, current_step_index=_resume_index(snapshot, len(plan.steps)),
                                     pending_step="", stop_reason=None, waiting_reason=None, waiting_source=None)
    return _run_with_replanning(
        plan,
        resumed,
        tool_runner,
        replanner_fn=replanner_fn,
        default_timeout_s=default_timeout_s,
        event_sink=event_sink,
        tool_details_by_name=tool_details_by_name,
        operation_contract_fingerprint=operation_contract_fingerprint,
        step_receipts=step_receipts,
        receipt_issuer=receipt_issuer,
        receipt_validator=receipt_validator,
        receipt_validator_factory=receipt_validator_factory,
        receipt_mode=receipt_mode,
        approved_step_id=snapshot.pending_step if snapshot.stop_reason == StopReason.RISK_GATE_REQUIRED else "",
    )
def _resume_index(snapshot: TaskLoopSnapshot, total_steps: int) -> int:
    if snapshot.stop_reason == StopReason.RISK_GATE_REQUIRED:
        return min(snapshot.current_step_index, total_steps)
    return min(snapshot.current_step_index + 1, total_steps)
