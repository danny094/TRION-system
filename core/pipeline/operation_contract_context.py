"""Read and validate OperationContract truth from pipeline context."""
from dataclasses import asdict
from collections.abc import Mapping
from enum import Enum
from typing import Any

from core.routing_frame.builder.contract_fingerprint import compute_operation_contract_fingerprint
from core.routing_frame.contracts import OperationContract


class ReceiptConfigurationState(str, Enum):
    LEGACY_VALID = "legacy_valid"
    RECEIPT_MODE_ACTIVE = "receipt_mode_active"
    INCONSISTENT_FAIL_CLOSED = "inconsistent_fail_closed"


def operation_contract_from_context(context: Any) -> Mapping[str, Any]:
    contract = typed_operation_contract_from_context(context)
    fingerprint = _fingerprint_value(context)
    return asdict(contract) if contract is not None and _fingerprint_matches(contract, fingerprint) else {}


def typed_operation_contract_from_context(context: Any) -> OperationContract | None:
    return _rehydrate_contract(_contract_value(context))


def operation_contract_fingerprint_from_context(context: Any) -> str:
    if not isinstance(context, Mapping):
        return ""
    direct = _fingerprint_string(context.get("operation_contract_fingerprint"))
    if direct:
        return direct
    for frame in _frames(context):
        fingerprint = _fingerprint_string(frame.get("operation_contract_fingerprint"))
        if fingerprint:
            return fingerprint
    return ""


def receipt_configuration_state(
    context: Any, *, receipt_provenance: bool = False, receipt_callbacks: bool = False,
    receipt_history_present: bool = True,
) -> ReceiptConfigurationState:
    contract = _contract_value(context)
    fingerprint = _fingerprint_value(context)
    has_contract = contract is not None
    has_fingerprint = fingerprint is not None
    if not has_contract and not has_fingerprint and not receipt_provenance and not receipt_callbacks:
        return ReceiptConfigurationState.LEGACY_VALID
    if not receipt_history_present:
        return ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED
    typed_contract = _rehydrate_contract(contract)
    if typed_contract is not None and _fingerprint_matches(typed_contract, fingerprint):
        return ReceiptConfigurationState.RECEIPT_MODE_ACTIVE
    return ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED


def operation_receipt_mode_active(context: Any) -> bool:
    """Compatibility projection from the canonical tri-state."""
    return receipt_configuration_state(context) is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE


def _rehydrate_contract(value: Any) -> OperationContract | None:
    return OperationContract.from_dict(value)


def _fingerprint_matches(contract: OperationContract, value: Any) -> bool:
    return _nonempty_string(value) and value == compute_operation_contract_fingerprint(contract)


def _nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _contract_value(context: Any) -> Any:
    for frame in _frames(context):
        if "operation_contract" in frame:
            return frame.get("operation_contract")
    return None


def _fingerprint_value(context: Any) -> Any:
    if isinstance(context, Mapping) and "operation_contract_fingerprint" in context:
        return context.get("operation_contract_fingerprint")
    for frame in _frames(context):
        if "operation_contract_fingerprint" in frame:
            return frame.get("operation_contract_fingerprint")
    return None


def _frames(context: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(context, Mapping):
        return ()
    nested = context.get("context") if isinstance(context.get("context"), Mapping) else {}
    orchestrator = context.get("orchestrator") if isinstance(context.get("orchestrator"), Mapping) else {}
    nested_orchestrator = orchestrator.get("context") if isinstance(orchestrator.get("context"), Mapping) else {}
    return tuple(
        frame for frame in (context.get("routing_frame"), nested.get("routing_frame"), nested_orchestrator.get("routing_frame"))
        if isinstance(frame, Mapping)
    )


def _fingerprint_string(value: Any) -> str:
    return value.strip() if type(value) is str else ""
