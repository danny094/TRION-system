import pytest

from core.task_loop import tool_execution_contracts
from adapters import tool_runner_bridge
from adapters.tool_runner_bridge import get_available_tools, make_tool_runner
from core.orchestrator.tools import list_available_tools
from core.task_loop import executor
from core.task_loop.executable_now import details_by_name
from core.task_loop.executor import TaskToolResultStatus, execute_step
from core.thinking.contracts import PlanStep
from mcp.catalog_contracts import (
    MCPDesiredState,
    MCPToolCatalogSnapshot,
    MCPTransportBindingOutcome,
    MCPTransportBindingStatus,
    make_route,
)
from mcp.catalog_lifecycle import publish_catalog, revoke_catalog_routes
from mcp.hub import MCPHub
from mcp.structural_validation_contracts import MCPStructuralValidationStatus as StructuralStatus
from mcp.structural_validator import validate_structured_output
from mcp.tool_result_contracts import (
    MCPResultPresence as Presence,
    MCPToolCallStatus as ToolStatus,
    MCPToolResultEnvelope,
)
def test_executor_reexports_split_contracts_without_duplicate_types():
    assert executor.TaskToolCall is tool_execution_contracts.TaskToolCall
    assert executor.TaskToolResultStatus is tool_execution_contracts.TaskToolResultStatus
    assert executor.TaskToolResult is tool_execution_contracts.TaskToolResult
def _step() -> PlanStep:
    return PlanStep(
        step_id="step-1",
        title="Inspect",
        goal="Inspect the demo resource",
        tool="demo_inspect",
        tool_arguments={"resource": "demo"},
    )
def _intent(schema_version: int) -> dict:
    if schema_version == 1:
        return {
            "name": "demo_inspect",
            "description": "Inspect a demo resource.",
            "tool_intent_meta": {
                "schema_version": 1,
                "source_sha256": "b" * 64,
                "bundle_version": "1.0.0",
            },
        }
    return {
        "name": "demo_inspect",
        "description": "Inspect a demo resource.",
        "requires": ["resource"],
        "evidence_types": ["runtime_metadata"],
        "risk": "read_only",
        "target_scopes": ["runtime_state"],
        "freshness_support": "live_only",
        "tool_role": "primary",
        "output_schema": "mcp_output_schema",
        "capability_complete": True,
        "tool_intent_meta": {
            "schema_version": 2,
            "source_sha256": "a" * 64,
            "bundle_version": "2.1.0",
        },
    }


class _OfflineTransport:
    def __init__(self, envelope: MCPToolResultEnvelope):
        self.envelope = envelope
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, dict(arguments)))
        return self.envelope


def _run_real_chain(monkeypatch, *, schema, envelope, schema_version=2):
    import mcp.config as mcp_config
    import mcp.hub as hub_module

    intent = _intent(schema_version)
    config = {"enabled": True, "tool_intents": {"tools": [intent]}}
    tool_definition = {"name": "demo_inspect", "description": intent["description"]}
    if schema is not None:
        tool_definition["outputSchema"] = schema
    transport = _OfflineTransport(envelope)
    snapshot = MCPToolCatalogSnapshot.from_parts(
        MCPDesiredState({"demo-mcp": config}, {}),
        {"demo-mcp": MCPTransportBindingOutcome(MCPTransportBindingStatus.BOUND, transport)},
        {"demo-mcp": None},
        {"demo-mcp": {"online": True, "routable": True}},
        {"demo_inspect": make_route("demo_inspect", "demo-mcp", transport, tool_definition)},
        {},
    )
    publish_catalog(snapshot)
    hub = MCPHub()
    hub._initialized = True
    monkeypatch.setattr(hub_module, "_hub", hub)
    monkeypatch.setattr(mcp_config, "get_all_mcps", lambda: {"demo-mcp": config})
    validator_calls = []

    def counted_validator(output_schema, result_envelope):
        validator_calls.append((output_schema, result_envelope))
        return validate_structured_output(output_schema, result_envelope)

    monkeypatch.setattr(tool_runner_bridge, "validate_structured_output", counted_validator)
    available_tools = list_available_tools(get_available_tools())
    seen = {}
    runner = make_tool_runner()

    def capturing_runner(tool_call):
        seen["tool_call"] = tool_call
        seen["task_result"] = runner(tool_call)
        return seen["task_result"]

    try:
        execution = execute_step(
            _step(),
            capturing_runner,
            tool_details_by_name=details_by_name(available_tools),
        )
    finally:
        revoke_catalog_routes(lambda _transport: None)
    return execution, seen, validator_calls, transport.calls


def _success(value: dict) -> MCPToolResultEnvelope:
    return MCPToolResultEnvelope(
        ToolStatus.SUCCESS,
        structured_content_presence=Presence.VALUE if value else Presence.EMPTY,
        structured_content=value,
    )


def test_real_tools_list_and_call_chain_preserves_valid_result(monkeypatch):
    schema = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    }
    envelope = _success({"value": 1})

    execution, seen, validator_calls, transport_calls = _run_real_chain(
        monkeypatch,
        schema=schema,
        envelope=envelope,
    )

    assert execution.status.value == "success", execution.error
    assert transport_calls == [("demo_inspect", {"resource": "demo"})]
    assert validator_calls == [(schema, envelope)]
    assert seen["task_result"].status is TaskToolResultStatus.SUCCESS_VALUE
    assert seen["task_result"].structural_result.status is StructuralStatus.VALID
    assert seen["task_result"].structural_result.envelope is envelope
    assert seen["tool_call"].output_schema_mapping() == schema
    with pytest.raises(TypeError):
        seen["tool_call"].output_schema["properties"]["value"] = {"type": "string"}


def test_missing_schema_stays_separate_from_success(monkeypatch):
    execution, seen, validator_calls, _transport_calls = _run_real_chain(
        monkeypatch,
        schema=None,
        envelope=_success({"value": 1}),
        schema_version=1,
    )

    assert execution.status.value == "success", execution.error
    assert validator_calls[0][0] is None
    assert seen["tool_call"].output_schema is None
    assert seen["task_result"].status is TaskToolResultStatus.SUCCESS_VALUE
    assert seen["task_result"].structural_result.status is StructuralStatus.OUTPUT_SCHEMA_MISSING


def test_instance_mismatch_does_not_reclassify_execution(monkeypatch):
    execution, seen, _validator_calls, _transport_calls = _run_real_chain(
        monkeypatch,
        schema={"type": "object", "required": ["value"]},
        envelope=_success({}),
    )

    assert execution.status.value == "success", execution.error
    assert seen["task_result"].status is TaskToolResultStatus.SUCCESS_EMPTY
    assert seen["task_result"].structural_result.status is StructuralStatus.INSTANCE_MISMATCH


def test_malformed_schema_reaches_validator_without_blocking_execution(monkeypatch):
    execution, seen, validator_calls, transport_calls = _run_real_chain(
        monkeypatch,
        schema={"type": object()},
        envelope=_success({"value": 1}),
    )

    assert execution.status.value == "success", execution.error
    assert transport_calls == [("demo_inspect", {"resource": "demo"})]
    assert len(validator_calls) == 1
    assert seen["task_result"].status is TaskToolResultStatus.SUCCESS_VALUE
    assert seen["task_result"].structural_result.status is StructuralStatus.OUTPUT_SCHEMA_MALFORMED
