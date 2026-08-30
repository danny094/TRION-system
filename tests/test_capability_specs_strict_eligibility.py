"""Fail-closed domain, operation-family and risk locks for T_eligible."""

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from tests.operation_contract_context import canonical_contract_context


def _contract(**overrides):
    contract = canonical_contract_context(
        required_evidence=("runtime_status",),
    )["routing_frame"]["operation_contract"]
    contract.update(overrides)
    return contract


def _tool(**overrides):
    fields = {
        "name": "container_list",
        "capability_domain": "container_runtime",
        "capability_operation": "list",
        "capability_evidence_types": ["runtime_status"],
        "capability_target_scopes": ["runtime_state"],
        "capability_risk": "read_only",
    }
    fields.update(overrides)
    return ToolDescriptor(**fields)


def test_query_operation_matches_search_contract_family():
    tool = _tool(capability_operation="query")
    contract = _contract(primary_operation="search", allowed_operations=["search"])

    assert eligible_tools_for_contract([tool], contract) == [tool]


def test_partial_raw_contract_blocks_before_scope_eligibility():
    partial = {
        "domain": "container_runtime",
        "primary_operation": "list",
        "required_evidence": ["runtime_status"],
        "allowed_operations": ["list"],
        "mutating_action": False,
    }

    assert eligible_tools_for_contract([_tool()], partial) == []


def test_empty_or_wrong_domain_blocks():
    assert eligible_tools_for_contract([_tool()], _contract(domain="")) == []
    assert eligible_tools_for_contract(
        [_tool(capability_domain="files")], _contract()
    ) == []


def test_missing_capability_risk_blocks():
    assert eligible_tools_for_contract(
        [_tool(capability_risk="")], _contract()
    ) == []


def test_contract_operation_and_mutation_semantics_must_be_exact():
    risky = _tool(capability_risk="mutating")

    assert eligible_tools_for_contract(
        [_tool()], _contract(allowed_operations=["list", "inspect"])
    ) == []
    assert eligible_tools_for_contract(
        [risky], _contract(mutating_action=True)
    ) == []


def test_mutating_action_rejects_read_only_risk_label():
    tool = _tool(
        name="container_restart",
        capability_operation="execute",
        capability_risk="read_only",
    )
    contract = _contract(
        primary_operation="execute",
        allowed_operations=["execute"],
        mutating_action=True,
        required_evidence=[],
    )

    assert eligible_tools_for_contract([tool], contract) == []
