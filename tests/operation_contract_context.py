from dataclasses import asdict
from typing import Any

from core.routing_frame.builder.contract_fingerprint import compute_operation_contract_fingerprint
from core.routing_frame.contracts import OperationContract, OperationTransition


def canonical_contract_context(
    *, domain: str = "container_runtime", primary_operation: str = "list",
    target: str = "internal", detail_fields: tuple[str, ...] = (),
    targets: tuple[str, ...] | None = None,
    mutating_action: bool = False, required_evidence: tuple[str, ...] = (),
    allowed_operations: tuple[str, ...] = ("list",),
    allowed_transitions: tuple[str, ...] = (),
    transition_requirements: tuple[OperationTransition, ...] = (),
    scope_lock: str = "internal", fingerprint: Any = None,
) -> dict[str, Any]:
    contract = OperationContract(
        domain=domain, primary_operation=primary_operation, target=target,
        targets=targets if targets is not None else ((target,) if target else ()),
        detail_fields=detail_fields, mutating_action=mutating_action,
        required_evidence=required_evidence, allowed_operations=allowed_operations,
        allowed_transitions=tuple(item.edge for item in transition_requirements),
        transition_requirements=transition_requirements,
        scope_lock=scope_lock, provenance={},
    )
    canonical = compute_operation_contract_fingerprint(contract)
    return {"routing_frame": {
        "operation_contract": asdict(contract),
        "operation_contract_fingerprint": canonical if fingerprint is None else fingerprint,
    }}
