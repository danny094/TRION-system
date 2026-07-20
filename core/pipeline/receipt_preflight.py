"""Approve preflight through the existing receipt issuer and validator."""
from typing import Any

from core.task_loop.receipt_flow import receipt_for_step
from core.task_loop.step_operation_receipt import StepOperationReceipt


def preflight_current_step_receipt(plan: Any, snapshot: Any, issuer: Any, validator: Any) -> bool:
    steps = list(getattr(plan, "steps", []) or [])
    index = getattr(snapshot, "current_step_index", -1)
    if type(index) is not int or index < 0 or index >= len(steps):
        return False
    receipt = receipt_for_step(steps[index], plan, snapshot, {}, issuer, validator)
    return type(receipt) is StepOperationReceipt
