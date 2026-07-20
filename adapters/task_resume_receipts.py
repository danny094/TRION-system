"""Strict internal Receipt/Execution snapshot parsing."""
from typing import Any

from core.task_loop.contracts import StepExecutionStatus, StepOperationExecution
from core.task_loop.step_operation_receipt import StepOperationReceipt


def step_operation_executions(value: Any) -> list[StepOperationExecution]:
    if type(value) is not list:
        raise ValueError("invalid_step_operation_executions")
    result: list[StepOperationExecution] = []
    for row in value:
        if type(row) is not dict or type(row.get("receipt")) is not dict:
            raise ValueError("invalid_step_operation_execution")
        data = row["receipt"]
        step_id = data.get("step_id")
        operation = data.get("operation")
        fingerprint = data.get("operation_contract_fingerprint")
        if not all(type(item) is str and item and item == item.strip() for item in (step_id, operation, fingerprint)):
            raise ValueError("invalid_step_operation_receipt")
        if type(data.get("scope_preserved")) is not bool:
            raise ValueError("invalid_step_operation_scope")
        try:
            status = StepExecutionStatus(row.get("status"))
        except (TypeError, ValueError):
            raise ValueError("invalid_step_operation_status") from None
        result.append(StepOperationExecution(
            StepOperationReceipt(step_id, operation, fingerprint, data["scope_preserved"]), status
        ))
    return result
