"""Fail-closed receipt issuance from existing OperationContract truth."""
from collections.abc import Mapping
from typing import Any

from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, StepOperationExecution
from core.task_loop.step_operation_receipt import StepOperationReceipt


def issue_initial_receipt(step_id: Any, contract: Mapping[str, Any], fingerprint: str) -> StepOperationReceipt | None:
    operation = _clean(contract.get("primary_operation"))
    allowed = _values(contract.get("allowed_operations"))
    if not _clean(step_id) or not fingerprint or not operation or operation not in allowed:
        return None
    return StepOperationReceipt(str(step_id), operation, fingerprint, scope_preserved=True)


def issue_followup_receipt(
    step_id: Any,
    predecessor: StepExecutionResult | StepOperationExecution | None,
    contract: Mapping[str, Any],
    fingerprint: str,
) -> StepOperationReceipt | None:
    receipt = getattr(predecessor, "receipt", None)
    if (
        not isinstance(receipt, StepOperationReceipt)
        or getattr(predecessor, "status", None) is not StepExecutionStatus.SUCCESS
        or receipt.scope_preserved is not True
        or receipt.operation_contract_fingerprint != fingerprint
        or not _clean(step_id)
    ):
        return None
    transition = _transition_requirement(receipt.operation, contract.get("transition_requirements"))
    if transition is None:
        return None
    return StepOperationReceipt(str(step_id), transition[0], fingerprint, scope_preserved=True)


def contract_for_receipt(
    contract: Mapping[str, Any],
    receipt: StepOperationReceipt | None,
    fingerprint: str,
    predecessor: StepExecutionResult | StepOperationExecution | None = None,
) -> dict[str, Any]:
    if not isinstance(receipt, StepOperationReceipt) or receipt.scope_preserved is not True:
        return {}
    if not fingerprint or receipt.operation_contract_fingerprint != fingerprint:
        return {}
    primary = _clean(contract.get("primary_operation"))
    if predecessor is None:
        if receipt.operation != primary or receipt.operation not in _values(contract.get("allowed_operations")):
            return {}
    elif not _valid_followup(receipt, predecessor, fingerprint, contract.get("transition_requirements")):
        return {}
    projected = dict(contract)
    projected["primary_operation"] = receipt.operation
    projected["allowed_operations"] = [receipt.operation]
    if predecessor is not None:
        previous = getattr(predecessor, "receipt", None)
        transition = _transition_requirement(
            getattr(previous, "operation", ""), contract.get("transition_requirements"),
        )
        if transition is None or transition[0] != receipt.operation:
            return {}
        projected["required_evidence"] = list(transition[1])
    return projected


def _valid_followup(receipt, predecessor, fingerprint: str, transitions: Any) -> bool:
    previous = getattr(predecessor, "receipt", None)
    transition = _transition_requirement(getattr(previous, "operation", ""), transitions)
    return (
        getattr(predecessor, "status", None) is StepExecutionStatus.SUCCESS
        and isinstance(previous, StepOperationReceipt)
        and previous.scope_preserved is True
        and previous.operation_contract_fingerprint == fingerprint
        and transition is not None
        and transition[0] == receipt.operation
    )


def _transition_requirement(operation: str, values: Any) -> tuple[str, tuple[str, ...]] | None:
    matches = []
    for value in values if isinstance(values, (list, tuple)) else ():
        if not isinstance(value, Mapping) or _clean(value.get("source_operation")) != operation:
            continue
        target = _clean(value.get("target_operation"))
        evidence = _values(value.get("required_evidence"))
        if target:
            matches.append((target, evidence))
    return matches[0] if len(matches) == 1 else None


def _values(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(_clean(item) for item in value if _clean(item))
    except TypeError:
        return ()


def _clean(value: Any) -> str:
    return str(value or "").strip()
