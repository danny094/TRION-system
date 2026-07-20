from dataclasses import asdict
from typing import Any

from core.routing_frame.builder.contract_fingerprint import compute_operation_contract_fingerprint
from core.routing_frame.contracts import OperationContract


def canonical_contract_context(
    *, domain: str = "container_runtime", primary_operation: str = "list",
    target: str = "internal", detail_fields: tuple[str, ...] = (),
    mutating_action: bool = False, required_evidence: tuple[str, ...] = (),
    allowed_operations: tuple[str, ...] = ("list",),
    allowed_transitions: tuple[str, ...] = ("list->logs",),
    scope_lock: str = "internal", fingerprint: Any = None,
) -> dict[str, Any]:
    contract = OperationContract(
        domain=domain, primary_operation=primary_operation, target=target,
        detail_fields=detail_fields, mutating_action=mutating_action,
        required_evidence=required_evidence, allowed_operations=allowed_operations,
        allowed_transitions=allowed_transitions, scope_lock=scope_lock, provenance={},
    )
    canonical = compute_operation_contract_fingerprint(contract)
    return {"routing_frame": {
        "operation_contract": asdict(contract),
        "operation_contract_fingerprint": canonical if fingerprint is None else fingerprint,
    }}
