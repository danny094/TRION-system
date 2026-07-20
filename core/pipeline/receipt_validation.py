"""Plan-position and receipt validation at the PlanContract boundary."""
from typing import Any, Callable

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.pipeline.plan_contract_validator import authorized_contract_for_receipt
from core.task_loop.contracts import StepExecutionStatus, StepOperationExecution
from core.task_loop.step_operation_receipt import ReceiptValidationContext, StepOperationReceipt
from core.thinking.contracts import ThinkingPlan


def build_step_receipt_validator(context: Any, tools: Any, plan: ThinkingPlan) -> Callable:
    descriptors = [tool for tool in list(tools or []) if isinstance(tool, ToolDescriptor)]
    planned = list(plan.steps)
    planned_ids = tuple(getattr(step, "step_id", None) for step in planned)

    def _validate(step: Any, receipt: Any, provenance: ReceiptValidationContext) -> Any:
        executions = _validated_prefix(provenance, planned_ids, planned, _valid_for_step)
        if executions is None or provenance.current_step_index >= len(planned):
            return None
        current = planned[provenance.current_step_index]
        if current is not step and getattr(current, "step_id", None) != getattr(step, "step_id", None):
            return None
        predecessor = executions[-1] if executions else None
        return receipt if _valid_for_step(current, receipt, predecessor) else None

    def _valid_for_step(step: Any, receipt: Any, predecessor: Any) -> bool:
        if getattr(receipt, "step_id", None) != getattr(step, "step_id", None):
            return False
        contract = authorized_contract_for_receipt(receipt, context=context, predecessor=predecessor)
        matches = [tool for tool in descriptors if tool.name == getattr(step, "tool", None)]
        return bool(contract) and len(matches) == 1 and matches[0] in eligible_tools_for_contract(descriptors, contract)

    return _validate


def build_step_receipt_validator_factory(context: Any, tools: Any) -> Callable:
    return lambda plan: build_step_receipt_validator(context, tools, plan) if isinstance(plan, ThinkingPlan) else None


def _validated_prefix(
    provenance: Any, planned_ids: tuple[Any, ...], planned: list[Any], validate_step: Callable,
) -> tuple[StepOperationExecution, ...] | None:
    if type(provenance) is not ReceiptValidationContext:
        return None
    if any(type(step_id) is not str or not step_id or step_id != step_id.strip() for step_id in planned_ids):
        return None
    if len(set(planned_ids)) != len(planned_ids) or provenance.plan_step_ids != planned_ids:
        return None
    index = provenance.current_step_index
    if type(index) is not int or index < 0 or index > len(planned_ids):
        return None
    if provenance.completed_steps != planned_ids[:index] or len(provenance.executions) != index:
        return None
    validated: list[StepOperationExecution] = []
    previous = None
    for position, execution in enumerate(provenance.executions):
        if (
            type(execution) is not StepOperationExecution
            or type(execution.receipt) is not StepOperationReceipt
            or execution.status is not StepExecutionStatus.SUCCESS
            or execution.receipt.step_id != planned_ids[position]
            or not validate_step(planned[position], execution.receipt, previous)
        ):
            return None
        validated.append(execution)
        previous = execution
    expected_current = planned_ids[index] if index < len(planned_ids) else None
    if provenance.current_step_id != expected_current:
        return None
    return tuple(validated)
