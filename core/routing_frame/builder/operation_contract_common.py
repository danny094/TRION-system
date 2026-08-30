"""Shared OperationContract construction helpers extracted before P11 R5."""
from __future__ import annotations

from core.routing_frame.contracts import OperationContract
from core.routing_frame.operation_contract_invariants import MUTATING_OPERATIONS

_PREDICATE_AMBIGUOUS_CONFIDENCE = 0.5


def _build(
    domain,
    operation,
    target,
    detail_fields,
    scope_lock,
    meaning,
    required_evidence,
    transition_requirements,
):
    if _predicate_ambiguous(meaning) and not transition_requirements:
        return _incomplete(domain, target, detail_fields, scope_lock, meaning)
    return OperationContract(
        domain=domain,
        primary_operation=operation,
        target=target,
        targets=tuple(meaning.target_candidates),
        detail_fields=detail_fields,
        mutating_action=operation in MUTATING_OPERATIONS,
        required_evidence=required_evidence,
        allowed_operations=(operation,),
        allowed_transitions=tuple(item.edge for item in transition_requirements),
        transition_requirements=transition_requirements,
        scope_lock=scope_lock,
        provenance=dict(meaning.provenance),
    )


def _predicate_ambiguous(meaning):
    predicate_prov = meaning.provenance.get("predicate")
    return bool(
        predicate_prov
        and predicate_prov.confidence == _PREDICATE_AMBIGUOUS_CONFIDENCE
    )


def _incomplete(domain, target, detail_fields, scope_lock, meaning):
    return OperationContract(
        domain=domain,
        primary_operation="",
        target=target,
        targets=tuple(meaning.target_candidates),
        detail_fields=detail_fields,
        mutating_action=False,
        required_evidence=(),
        allowed_operations=(),
        allowed_transitions=(),
        transition_requirements=(),
        scope_lock=scope_lock,
        provenance=dict(meaning.provenance),
    )
