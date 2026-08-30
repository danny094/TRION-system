"""Composite OperationContract initial eligibility consumer proof."""

import json
from pathlib import Path

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_descriptor_projection import descriptor_from_raw
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.routing_frame.contracts import OperationTransition
from tests.operation_contract_context import canonical_contract_context


_BUNDLE_INTENTS = Path("examples/container_commander_bundle/tool_intents.json")
_OUTPUT_SCHEMAS = Path("mcp-servers/container-commander/output_schemas.json")


def _contract() -> dict:
    return canonical_contract_context(
        target="trion-home", required_evidence=("runtime_status",), scope_lock="home",
        transition_requirements=(OperationTransition("list", "logs", ("runtime_logs",)),),
    )["routing_frame"]["operation_contract"]


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


def _bundle_descriptor(name: str) -> ToolDescriptor:
    payload = json.loads(_BUNDLE_INTENTS.read_text(encoding="utf-8"))
    output_schemas = json.loads(_OUTPUT_SCHEMAS.read_text(encoding="utf-8"))
    tool_intent = next(tool for tool in payload["tools"] if tool["name"] == name)
    tool_intent["capability_complete"] = True
    tool_intent["tool_intent_meta"] = {
        "schema_version": payload["schema_version"],
        "source_sha256": "a" * 64,
        "bundle_version": "2.1.0",
    }
    descriptor = descriptor_from_raw({
        "name": name,
        "tool_intent": tool_intent,
        "outputSchema": output_schemas[name],
    })
    assert descriptor is not None
    return descriptor


def test_container_commander_source_allows_composite_list_then_logs():
    list_contract = _contract()
    logs_contract = {
        **list_contract,
        "primary_operation": "logs",
        "required_evidence": ["runtime_logs"],
        "allowed_operations": ["logs"],
    }

    assert [
        tool.name
        for tool in eligible_tools_for_contract([_bundle_descriptor("container_list")], list_contract)
    ] == ["container_list"]
    assert [
        tool.name
        for tool in eligible_tools_for_contract([_bundle_descriptor("container_logs")], logs_contract)
    ] == ["container_logs"]
