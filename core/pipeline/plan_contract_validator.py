from dataclasses import dataclass, field
from functools import wraps
from collections.abc import Iterable, Mapping
from typing import Any

from core.pipeline.operation_contract_context import (
    ReceiptConfigurationState, operation_contract_fingerprint_from_context,
    operation_contract_from_context, receipt_configuration_state,
)
from core.pipeline.plan_contract_metadata import validate_plan_step_ids, validate_tool_metadata
from core.pipeline.step_operation_receipts import (
    contract_for_receipt,
    issue_followup_receipt,
    issue_initial_receipt,
)
from core.task_loop.contracts import StepExecutionResult, StepOperationExecution
from core.task_loop.step_operation_receipt import StepOperationReceipt
from core.thinking.contracts import PlanContractViolation, ThinkingPlan


@dataclass(frozen=True)
class PlanContractDecision:
    allowed: bool
    reason: str = ""
    unknown_tools: list[str] = field(default_factory=list)


_MISSING = object()


def validate_plan_contract(
    plan: ThinkingPlan,
    tool_truth: Any,
    *,
    context: Mapping[str, Any] | None = None,
    stored_fingerprint: Any = _MISSING,
    require_fingerprint: bool = True,
) -> PlanContractDecision:
    step_reason = validate_plan_step_ids(plan)
    if step_reason:
        return PlanContractDecision(False, step_reason)
    decision = validate_plan_tools(plan, tool_truth)
    planned_tools = _planned_tools(plan)
    if not decision.allowed or not planned_tools:
        return decision
    metadata_reason = validate_tool_metadata(planned_tools, tool_truth)
    if metadata_reason:
        return PlanContractDecision(allowed=False, reason=metadata_reason)
    if require_fingerprint is not True:
        return PlanContractDecision(allowed=True)
    return validate_plan_fingerprint(context=context, stored_fingerprint=stored_fingerprint)


def validate_plan_tools(plan: ThinkingPlan, tool_truth: Any) -> PlanContractDecision:
    allowed_tools = _tool_names(tool_truth)
    unknown = [tool for tool in _planned_tools(plan) if tool not in allowed_tools]
    if unknown:
        return PlanContractDecision(
            allowed=False,
            reason=f"plan_contract_unknown_tool:{','.join(unknown)}",
            unknown_tools=unknown,
        )
    return PlanContractDecision(allowed=True)


def tool_truth_from_context(context: Mapping[str, Any] | None) -> Any:
    if not isinstance(context, Mapping):
        return []
    for key in ("selected_tool_details", "selected_tools", "available_tool_details", "available_tools"):
        if key in context:
            return context.get(key)
    return []


def validate_plan_fingerprint(
    *,
    context: Mapping[str, Any] | None = None,
    stored_fingerprint: Any = _MISSING,
) -> PlanContractDecision:
    routing_fingerprint = operation_contract_fingerprint_from_context(context)
    if receipt_configuration_state(context) is not ReceiptConfigurationState.RECEIPT_MODE_ACTIVE:
        return PlanContractDecision(
            allowed=False,
            reason="plan_contract_fingerprint_mismatch" if routing_fingerprint else "plan_contract_missing_fingerprint",
        )
    has_stored = stored_fingerprint is not _MISSING
    stored = _clean_fingerprint(stored_fingerprint) if has_stored else ""
    if has_stored and not stored:
        return PlanContractDecision(
            allowed=False,
            reason="plan_contract_missing_fingerprint",
        )
    if has_stored and not routing_fingerprint:
        return PlanContractDecision(
            allowed=False,
            reason="plan_contract_missing_fingerprint",
        )
    if has_stored and stored != routing_fingerprint:
        return PlanContractDecision(
            allowed=False,
            reason="plan_contract_fingerprint_mismatch",
        )
    expected = stored if has_stored else routing_fingerprint
    if not expected:
        return PlanContractDecision(
            allowed=False,
            reason="plan_contract_missing_fingerprint",
        )
    return PlanContractDecision(allowed=True)
def issue_initial_step_receipt(step_id: str, *, context: Any) -> StepOperationReceipt | None:
    return issue_initial_receipt(
        step_id,
        operation_contract_from_context(context),
        operation_contract_fingerprint_from_context(context),
    )
def issue_followup_step_receipt(
    step_id: str,
    predecessor: StepExecutionResult | StepOperationExecution | None,
    *,
    context: Any,
) -> StepOperationReceipt | None:
    return issue_followup_receipt(
        step_id,
        predecessor,
        operation_contract_from_context(context),
        operation_contract_fingerprint_from_context(context),
    )
def authorized_contract_for_receipt(
    receipt: StepOperationReceipt | None,
    *,
    context: Any,
    predecessor: StepExecutionResult | StepOperationExecution | None = None,
) -> dict[str, Any]:
    return contract_for_receipt(
        operation_contract_from_context(context),
        receipt,
        operation_contract_fingerprint_from_context(context),
        predecessor,
    )
def bind_validated_replanner(
    fn: Any,
    tool_truth: Any,
    *,
    context: Mapping[str, Any] | None = None,
    stored_fingerprint: Any = _MISSING,
) -> Any:
    if not callable(fn):
        return fn

    @wraps(fn)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        replanned = fn(*args, **kwargs)
        if not isinstance(replanned, ThinkingPlan):
            return replanned
        decision = validate_plan_contract(
            replanned,
            tool_truth,
            context=context,
            stored_fingerprint=stored_fingerprint,
        )
        if decision.allowed:
            return replanned
        raise PlanContractViolation(decision.reason)

    return _wrapped


def _planned_tools(plan: ThinkingPlan) -> list[str]:
    tools: list[str] = []
    for step in list(getattr(plan, "steps", []) or []):
        name = str(getattr(step, "tool", "") or "").strip()
        if name and name not in tools:
            tools.append(name)
    return tools


def _tool_names(tool_truth: Any) -> set[str]:
    names: set[str] = set()
    for item in _as_iterable(tool_truth):
        if isinstance(item, Mapping):
            name = str(item.get("name") or "").strip()
        elif isinstance(item, str):
            name = item.strip()
        else:
            name = str(getattr(item, "name", "") or "").strip()
        if name:
            names.add(name)
    return names


def _as_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        return []
    return value


def _clean_fingerprint(value: Any) -> str:
    return value.strip() if type(value) is str else ""
