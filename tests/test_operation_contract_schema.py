from dataclasses import asdict, fields

from core.pipeline.operation_contract_context import (
    ReceiptConfigurationState, receipt_configuration_state, typed_operation_contract_from_context,
)
from core.routing_frame.builder.contract_fingerprint import compute_operation_contract_fingerprint
from core.routing_frame.contracts import OperationContract
from tests.operation_contract_context import canonical_contract_context


def _typed() -> OperationContract:
    context = canonical_contract_context()
    parsed = OperationContract.from_dict(context["routing_frame"]["operation_contract"])
    assert type(parsed) is OperationContract
    return parsed


def test_typed_contract_and_mapping_roundtrip_preserve_fingerprint():
    contract = _typed()
    assert OperationContract.from_dict(contract) is contract
    restored = OperationContract.from_dict(asdict(contract))
    assert restored == contract
    assert compute_operation_contract_fingerprint(restored) == compute_operation_contract_fingerprint(contract)


def test_parser_field_set_is_derived_from_contract_and_fail_closed():
    raw = asdict(_typed())
    assert set(raw) == {item.name for item in fields(OperationContract)}
    for malformed in (
        {key: value for key, value in raw.items() if key != "domain"},
        {**raw, "future_field": "unexpected"},
        {**raw, "mutating_action": 1},
        {**raw, "allowed_operations": "list"},
        {**raw, "detail_fields": ["ok", 7]},
    ):
        assert OperationContract.from_dict(malformed) is None


def test_context_accepts_typed_contract_and_rejects_stale_fingerprint():
    contract = _typed()
    fingerprint = compute_operation_contract_fingerprint(contract)
    valid = {"routing_frame": {"operation_contract": contract, "operation_contract_fingerprint": fingerprint}}
    assert typed_operation_contract_from_context(valid) is contract
    assert receipt_configuration_state(valid) is ReceiptConfigurationState.RECEIPT_MODE_ACTIVE
    valid["routing_frame"]["operation_contract_fingerprint"] = "stale"
    assert receipt_configuration_state(valid) is ReceiptConfigurationState.INCONSISTENT_FAIL_CLOSED
