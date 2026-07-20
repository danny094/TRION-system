from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract


def test_missing_target_scopes_fail_closed_despite_matching_metadata():
    contract = {
        "domain": "container_runtime",
        "primary_operation": "list",
        "required_evidence": ["runtime_status"],
        "allowed_operations": ["list"],
        "mutating_action": False,
    }
    tool = ToolDescriptor(
        name="container_list",
        capability_domain="container_runtime",
        capability_operation="list",
        capability_evidence_types=["runtime_status"],
        capability_risk="read_only",
    )

    assert eligible_tools_for_contract([tool], contract) == []
