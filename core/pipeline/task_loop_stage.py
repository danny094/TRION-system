import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict

from core.task_loop.contracts import CompletionStatus, TaskLoopState
from core.task_loop.executable_now import details_by_name
from core.pipeline.common import public_task_loop_snapshot
from core.pipeline.composite_followup import build_composite_followup_planner
from core.pipeline.output_evidence_contracts import (
    OutputEvidenceHandoff, OutputEvidenceItem, OutputEvidenceState,
)
from core.pipeline.plan_contract_validator import (
    bind_validated_replanner,
    issue_followup_step_receipt,
    issue_initial_step_receipt,
    operation_contract_fingerprint_from_context,
)
from core.pipeline.operation_contract_context import ReceiptConfigurationState, receipt_configuration_state
from core.pipeline.receipt_validation import (
    attest_completed_execution, build_step_receipt_validator, build_step_receipt_validator_factory,
)
from core.pipeline.task_loop_bindings import (
    bind_replan_context as _bind_replan_context,
    build_step_receipt_issuer,
)
from core.thinking.contracts import ThinkingPlan

TaskLoopFn = Callable[..., Any]
ToolRunner = Callable[[Any], Any]


@dataclass(frozen=True)
class TaskLoopStageResult:
    context: Dict[str, Any]
    result: Any = None
    output_evidence: OutputEvidenceHandoff = OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP)


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
    project_output_evidence_item: Callable[[object], OutputEvidenceItem | None] | None = None,
    attest_completed_execution_fn: Callable = attest_completed_execution,
) -> TaskLoopStageResult:
    if not plan.needs_task_loop:
        return TaskLoopStageResult(context={}, result=None)
    bound_replanner = bind_validated_replanner(
        _bind_replan_context(replanner_fn, available_tools, orchestrator_context),
        available_tools,
        context=orchestrator_context,
    )
    operation_contract_fingerprint = operation_contract_fingerprint_from_context(orchestrator_context)
    configuration = receipt_configuration_state(orchestrator_context)
    receipt_mode = configuration is not ReceiptConfigurationState.LEGACY_VALID
    active = configuration is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE
    descriptor_source = receipt_tool_descriptors if receipt_tool_descriptors is not None else available_tools
    evidence_source = descriptor_source if active else available_tools
    available_evidence_types: frozenset = frozenset(
        evidence
        for tool in (evidence_source or [])
        for evidence in (getattr(tool, "capability_evidence_types", None) or [])
    )
    tool_details = details_by_name(descriptor_source if active else available_tools)
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
        task_loop_kwargs["receipt_issuer"] = build_step_receipt_issuer(
            orchestrator_context, issue_initial_step_receipt, issue_followup_step_receipt,
        )
    receipt_validator = None
    if "receipt_validator" in signature.parameters and active:
        receipt_validator = build_step_receipt_validator(
            orchestrator_context, descriptor_source, plan,
        )
        task_loop_kwargs["receipt_validator"] = receipt_validator
        if "receipt_validator_factory" in signature.parameters:
            task_loop_kwargs["receipt_validator_factory"] = build_step_receipt_validator_factory(
                orchestrator_context, descriptor_source,
            )
    followup_planner = build_composite_followup_planner(
        orchestrator_context, descriptor_source, project_output_evidence_item,
    ) if active else None
    if "followup_planner" in signature.parameters and followup_planner is not None:
        task_loop_kwargs["followup_planner"] = followup_planner
    task_loop_result = task_loop_fn(plan, **task_loop_kwargs)
    complete = _completion_status_value(task_loop_result) == CompletionStatus.COMPLETE.value
    output_evidence = OutputEvidenceHandoff(OutputEvidenceState.TASK_LOOP_INCOMPLETE)
    if complete:
        attestation_plan = task_loop_result.active_plan if type(task_loop_result.active_plan) is ThinkingPlan else plan
        attestation_validator = (
            build_step_receipt_validator(orchestrator_context, descriptor_source, attestation_plan)
            if attestation_plan is not plan and active else receipt_validator
        )
        attestation = attest_completed_execution_fn(attestation_plan, task_loop_result, attestation_validator)
        projected = tuple(
            project_output_evidence_item(value)
            for value in task_loop_result.structural_results
        ) if callable(project_output_evidence_item) else ()
        valid = (
            attestation is not None
            and len(projected) == len(attestation.completed_step_ids)
            and all(type(item) is OutputEvidenceItem for item in projected)
        )
        output_evidence = OutputEvidenceHandoff(
            OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE if valid
            else OutputEvidenceState.COMPLETE_WITHOUT_VALIDATED_EVIDENCE,
            projected if valid else (),
        )
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
        output_evidence=output_evidence,
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
