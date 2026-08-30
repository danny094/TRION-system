from dataclasses import asdict, fields, replace

import pytest

from core.pipeline.operation_contract_context import (
    ReceiptConfigurationState, receipt_configuration_state, typed_operation_contract_from_context,
)
from core.routing_frame.builder.contract_fingerprint import compute_operation_contract_fingerprint
from core.routing_frame.contracts import (
    FieldProvenance,
    OperationContract,
    OperationTransition,
    RoutingFrame,
)
from tests.operation_contract_context import canonical_contract_context


def _typed() -> OperationContract:
    context = canonical_contract_context(
        transition_requirements=(
            OperationTransition("list", "logs", ("runtime_logs",)),
        ),
    )
    parsed = OperationContract.from_dict(context["routing_frame"]["operation_contract"])
    assert type(parsed) is OperationContract
    return parsed


def test_typed_contract_and_mapping_roundtrip_preserve_fingerprint():
    contract = _typed()
    assert contract.targets == (contract.target,)
    assert contract.transition_requirements[0].required_evidence == ("runtime_logs",)
    assert OperationContract.from_dict(contract) is contract
    restored = OperationContract.from_dict(asdict(contract))
    assert restored == contract
    assert compute_operation_contract_fingerprint(restored) == compute_operation_contract_fingerprint(contract)


def test_parser_field_set_is_derived_from_contract_and_fail_closed():
    raw = asdict(_typed())
    assert set(raw) == {item.name for item in fields(OperationContract)}
    for malformed in (
        {key: value for key, value in raw.items() if key != "domain"},
        {key: value for key, value in raw.items() if key != "transition_requirements"},
        {**raw, "future_field": "unexpected"},
        {**raw, "mutating_action": 1},
        {**raw, "allowed_operations": "list"},
        {**raw, "detail_fields": ["ok", 7]},
        {**raw, "transition_requirements": [{"source_operation": "list", "target_operation": "logs", "required_evidence": "runtime_logs"}]},
        {**raw, "allowed_transitions": []},
        {**raw, "targets": ["other"]},
        {**raw, "allowed_operations": ["list", "inspect"]},
        {**raw, "mutating_action": True},
    ):
        assert OperationContract.from_dict(malformed) is None


@pytest.mark.parametrize(
    "field_name",
    ("targets", "detail_fields", "required_evidence", "allowed_operations", "allowed_transitions"),
)
def test_typed_contract_rejects_mutable_sequence_fields(field_name):
    with pytest.raises(ValueError, match="operation_contract_tuple_field_invalid"):
        replace(_typed(), **{field_name: list(getattr(_typed(), field_name))})


def test_typed_instance_is_revalidated_instead_of_bypassing_parser():
    contract = _typed()
    object.__setattr__(contract, "mutating_action", True)

    assert OperationContract.from_dict(contract) is None


def test_contract_provenance_is_deeply_immutable():
    source = {"predicate": FieldProvenance("meaning", 1.0, "list")}
    contract = replace(_typed(), provenance=source)
    source.clear()

    assert tuple(contract.provenance) == ("predicate",)
    with pytest.raises(TypeError):
        contract.provenance["target"] = FieldProvenance("meaning", 1.0, "x")


def test_routing_frame_asdict_roundtrip_preserves_nonempty_provenance():
    contract = replace(
        _typed(),
        provenance={"predicate": FieldProvenance("meaning", 1.0, "list")},
    )
    frame = RoutingFrame(
        intent_kind="current_state_question",
        domain="container_runtime",
        evidence_need="runtime_logs",
        execution_mode="loop",
        dialogue_style="neutral",
        confidence=1.0,
        operation_contract=contract,
    )
    raw = asdict(frame)["operation_contract"]
    restored = OperationContract.from_dict(raw)

    assert restored == contract
    assert compute_operation_contract_fingerprint(restored) == compute_operation_contract_fingerprint(contract)
    provenance = raw["provenance"]["predicate"]
    for malformed in (
        {key: value for key, value in provenance.items() if key != "span"},
        {**provenance, "unexpected": "blocked"},
    ):
        assert OperationContract.from_dict({**raw, "provenance": {"predicate": malformed}}) is None


def test_context_accepts_typed_contract_and_rejects_stale_fingerprint():
    contract = _typed()
    fingerprint = compute_operation_contract_fingerprint(contract)
    valid = {"routing_frame": {"operation_contract": contract, "operation_contract_fingerprint": fingerprint}}
    assert typed_operation_contract_from_context(valid) is contract
    assert receipt_configuration_state(valid) is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE
    valid["routing_frame"]["operation_contract_fingerprint"] = "stale"
    assert receipt_configuration_state(valid) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED
