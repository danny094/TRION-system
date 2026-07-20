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
    targets = _transition_targets(receipt.operation, contract.get("allowed_transitions"))
    if len(targets) != 1:
        return None
    return StepOperationReceipt(str(step_id), targets[0], fingerprint, scope_preserved=True)


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
    elif not _valid_followup(receipt, predecessor, fingerprint, contract.get("allowed_transitions")):
        return {}
    projected = dict(contract)
    projected["primary_operation"] = receipt.operation
    projected["allowed_operations"] = [receipt.operation]
    return projected


def _valid_followup(receipt, predecessor, fingerprint: str, transitions: Any) -> bool:
    previous = getattr(predecessor, "receipt", None)
    return (
        getattr(predecessor, "status", None) is StepExecutionStatus.SUCCESS
        and isinstance(previous, StepOperationReceipt)
        and previous.scope_preserved is True
        and previous.operation_contract_fingerprint == fingerprint
        and len(_transition_targets(previous.operation, transitions)) == 1
        and _transition_targets(previous.operation, transitions)[0] == receipt.operation
    )


def _transition_targets(operation: str, values: Any) -> tuple[str, ...]:
    targets = []
    for value in _values(values):
        left, separator, right = value.partition("->")
        if separator and left == operation and right and right not in targets:
            targets.append(right)
    return tuple(targets)


def _values(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(_clean(item) for item in value if _clean(item))
    except TypeError:
        return ()


def _clean(value: Any) -> str:
    return str(value or "").strip()
