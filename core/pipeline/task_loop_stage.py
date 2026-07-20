import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict

from core.task_loop.contracts import CompletionStatus, TaskLoopState
from core.task_loop.executable_now import details_by_name
from core.pipeline.common import public_task_loop_snapshot
from core.pipeline.plan_contract_validator import (
    bind_validated_replanner,
    issue_followup_step_receipt,
    issue_initial_step_receipt,
    operation_contract_fingerprint_from_context,
)
from core.pipeline.operation_contract_context import ReceiptConfigurationState, receipt_configuration_state
from core.pipeline.receipt_validation import (
    build_step_receipt_validator, build_step_receipt_validator_factory,
)
from core.thinking.contracts import ThinkingPlan

TaskLoopFn = Callable[..., Any]
ToolRunner = Callable[[Any], Any]


def build_step_receipt_issuer(context: Any) -> Callable[[Any, Any], Any]:
    def _issue(step: Any, predecessor: Any) -> Any:
        step_id = str(getattr(step, "step_id", "") or "")
        return (
            issue_initial_step_receipt(step_id, context=context)
            if predecessor is None
            else issue_followup_step_receipt(step_id, predecessor, context=context)
        )
    return _issue


def _bind_replan_context(fn: Any, available_tools: Any, orchestrator_context: Any) -> Any:
    """Return fn wrapped to inject available_tools and orchestrator_context on every call."""
    if available_tools is None and orchestrator_context is None:
        return fn

    @functools.wraps(fn)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("available_tools", available_tools)
        kwargs.setdefault("orchestrator_context", orchestrator_context)
        return fn(*args, **kwargs)

    return _wrapped


@dataclass(frozen=True)
class TaskLoopStageResult:
    context: Dict[str, Any]
    result: Any = None


def build_task_loop_stage(
    plan: ThinkingPlan,
    *,
    conversation_id: str,
    objective: str,
    task_loop_fn: TaskLoopFn,
    tool_runner: ToolRunner,
    replanner_fn: Any,
    max_steps: int,
    max_retries_per_step: int,
    max_replans: int,
    loop_detection_enabled: bool = True,
    no_progress_threshold: int = 3,
    approval_mode: str = "risk_based",
    failure_escalation: str = "replan",
    approval_required_tools: list[str] | None = None,
    default_timeout_s: float = 30.0,
    event_sink: Any = None,
    available_tools: Any = None,
    receipt_tool_descriptors: Any = None,
    orchestrator_context: Any = None,
) -> TaskLoopStageResult:
    if not plan.needs_task_loop:
        return TaskLoopStageResult(context={}, result=None)
    bound_replanner = bind_validated_replanner(
        _bind_replan_context(replanner_fn, available_tools, orchestrator_context),
        available_tools,
        context=orchestrator_context,
    )
    available_evidence_types: frozenset = frozenset(
        et
        for tool in (available_tools or [])
        for et in (getattr(tool, "capability_evidence_types", None) or [])
    )
    tool_details = details_by_name(available_tools)
    operation_contract_fingerprint = operation_contract_fingerprint_from_context(orchestrator_context)
    configuration = receipt_configuration_state(orchestrator_context)
    receipt_mode = configuration is not ReceiptConfigurationState.LEGACY_VALID
    active = configuration is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE
    initial_receipt = issue_initial_step_receipt(plan.steps[0].step_id, context=orchestrator_context) if active and plan.steps else None
    signature = inspect.signature(task_loop_fn)
    task_loop_kwargs = {
        "conversation_id": conversation_id,
        "objective": objective,
        "tool_runner": tool_runner,
        "max_steps": max_steps,
        "max_retries_per_step": max_retries_per_step,
        "max_replans": max_replans,
    }
    if "loop_detection_enabled" in signature.parameters:
        task_loop_kwargs["loop_detection_enabled"] = loop_detection_enabled
    if "no_progress_threshold" in signature.parameters:
        task_loop_kwargs["no_progress_threshold"] = no_progress_threshold
    if "approval_mode" in signature.parameters:
        task_loop_kwargs["approval_mode"] = approval_mode
    if "failure_escalation" in signature.parameters:
        task_loop_kwargs["failure_escalation"] = failure_escalation
    if "default_timeout_s" in signature.parameters:
        task_loop_kwargs["default_timeout_s"] = default_timeout_s
    if "approval_required_tools" in signature.parameters:
        task_loop_kwargs["approval_required_tools"] = list(approval_required_tools or [])
    if "replanner_fn" in signature.parameters:
        task_loop_kwargs["replanner_fn"] = bound_replanner
    if "event_sink" in signature.parameters:
        task_loop_kwargs["event_sink"] = event_sink
    if "available_evidence_types" in signature.parameters:
        task_loop_kwargs["available_evidence_types"] = available_evidence_types
    if "tool_details_by_name" in signature.parameters:
        task_loop_kwargs["tool_details_by_name"] = tool_details
    if "operation_contract_fingerprint" in signature.parameters:
        task_loop_kwargs["operation_contract_fingerprint"] = operation_contract_fingerprint
    if "receipt_mode" in signature.parameters:
        task_loop_kwargs["receipt_mode"] = receipt_mode
    if "step_receipts" in signature.parameters and active:
        task_loop_kwargs["step_receipts"] = {initial_receipt.step_id: initial_receipt} if initial_receipt else {}
    if "receipt_issuer" in signature.parameters and active:
        task_loop_kwargs["receipt_issuer"] = build_step_receipt_issuer(orchestrator_context)
    if "receipt_validator" in signature.parameters and active:
        descriptor_source = receipt_tool_descriptors if receipt_tool_descriptors is not None else available_tools
        task_loop_kwargs["receipt_validator"] = build_step_receipt_validator(
            orchestrator_context, descriptor_source, plan,
        )
        if "receipt_validator_factory" in signature.parameters:
            task_loop_kwargs["receipt_validator_factory"] = build_step_receipt_validator_factory(
                orchestrator_context, descriptor_source,
            )
    task_loop_result = task_loop_fn(plan, **task_loop_kwargs)
    return TaskLoopStageResult(
        context={
            "task_loop": {
                "state": task_loop_result.state.value,
                "completion_status": _completion_status_value(task_loop_result),
                "stop_reason": task_loop_result.stop_reason.value if task_loop_result.stop_reason else None,
                "visible_content": task_loop_result.visible_content,
                "artifacts": task_loop_result.artifacts,
                "snapshot": public_task_loop_snapshot(task_loop_result.snapshot),
            }
        },
        result=task_loop_result,
    )


def _completion_status_value(task_loop_result: Any) -> str:
    status = getattr(task_loop_result, "completion_status", CompletionStatus.INCOMPLETE)
    value = status.value if isinstance(status, CompletionStatus) else str(status or "").strip().lower()
    if value and value != CompletionStatus.INCOMPLETE.value:
        return value
    state = getattr(task_loop_result, "state", None)
    if state == TaskLoopState.COMPLETED or str(state or "").strip().lower() == TaskLoopState.COMPLETED.value:
        return CompletionStatus.COMPLETE.value
    return CompletionStatus.INCOMPLETE.value
