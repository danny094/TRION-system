"""Composite OperationContract initial eligibility consumer proof."""

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract


def _contract() -> dict:
    return {
        "domain": "container_runtime",
        "primary_operation": "list",
        "target": "trion-home",
        "required_evidence": ["runtime_status"],
        "allowed_operations": ["list"],
        "allowed_transitions": ["list->logs"],
        "mutating_action": False,
        "scope_lock": "home",
    }


def _tool(name: str, operation: str) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        capability_domain="container_runtime",
        capability_operation=operation,
        capability_evidence_types=["runtime_status"],
        capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )


def test_composite_contract_does_not_initially_allow_followup_operation():
    eligible = eligible_tools_for_contract(
        [_tool("runtime_inventory", "list"), _tool("runtime_log_reader", "logs")],
        _contract(),
    )

    assert [tool.name for tool in eligible] == ["runtime_inventory"]
