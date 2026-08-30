"""Runtime invariants for the immutable OperationContract data shape."""

from collections.abc import Iterator, Mapping
from dataclasses import asdict
from types import MappingProxyType
from typing import Any


MUTATING_OPERATIONS = frozenset({"write", "update", "delete", "execute", "maintain"})
_STRING_TUPLE_FIELDS = (
    "targets",
    "detail_fields",
    "required_evidence",
    "allowed_operations",
    "allowed_transitions",
)


class FrozenProvenance(Mapping[str, Any]):
    """Read-only provenance mapping with an ``asdict``-safe deepcopy."""

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, Any]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __deepcopy__(self, _memo: dict[int, Any]) -> dict[str, Any]:
        return {key: asdict(value) for key, value in self._values.items()}


def validate_operation_contract(
    contract: Any, *, transition_type: type, provenance_type: type,
) -> None:
    for field_name in _STRING_TUPLE_FIELDS:
        values = getattr(contract, field_name)
        if type(values) is not tuple or any(
            type(value) is not str or not value or value != value.strip()
            for value in values
        ):
            raise ValueError(f"operation_contract_tuple_field_invalid:{field_name}")
    projected_target = contract.targets[0] if contract.targets else ""
    if contract.target != projected_target:
        raise ValueError("operation_contract_target_projection_mismatch")
    transitions = contract.transition_requirements
    if type(transitions) is not tuple or any(type(item) is not transition_type for item in transitions):
        raise ValueError("operation_contract_transition_type_invalid")
    projected_edges = tuple(item.edge for item in transitions)
    if contract.allowed_transitions != projected_edges or len(set(projected_edges)) != len(projected_edges):
        raise ValueError("operation_contract_transition_projection_mismatch")
    if contract.primary_operation:
        if contract.allowed_operations != (contract.primary_operation,):
            raise ValueError("operation_contract_allowed_operations_invalid")
        expected_mutation = contract.primary_operation in MUTATING_OPERATIONS
        if contract.mutating_action is not expected_mutation:
            raise ValueError("operation_contract_mutation_semantics_invalid")
    elif contract.allowed_operations or contract.mutating_action:
        raise ValueError("operation_contract_incomplete_semantics_invalid")
    provenance = contract.provenance
    if not isinstance(provenance, Mapping) or any(
        type(key) is not str or not key or type(value) is not provenance_type
        for key, value in provenance.items()
    ):
        raise ValueError("operation_contract_provenance_invalid")
    if type(provenance) is not FrozenProvenance:
        object.__setattr__(contract, "provenance", FrozenProvenance(provenance))
