"""Neutral typed receipt for validator-authorized semantic step operations."""
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class StepOperationReceipt:
    """Internal, non-event provenance issued only by PlanContractValidator."""

    step_id: str
    operation: str
    operation_contract_fingerprint: str
    scope_preserved: bool


@dataclass(frozen=True)
class ReceiptValidationContext:
    """Unmodified plan-position data transported to the pipeline validator."""

    plan_step_ids: tuple[Any, ...]
    current_step_index: Any
    completed_steps: tuple[Any, ...]
    executions: tuple[Any, ...]
    current_step_id: Any


ReceiptIssuer = Callable[[Any, Any], StepOperationReceipt | None]
ReceiptValidator = Callable[[Any, StepOperationReceipt, ReceiptValidationContext], StepOperationReceipt | None]
ReceiptValidatorFactory = Callable[[Any], ReceiptValidator | None]
