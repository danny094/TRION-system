from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_descriptor_projection import descriptor_from_raw
from core.task_loop.executable_now import details_by_name


_MISSING = object()


def _raw_tool(output_schema=_MISSING, *, schema_version=2, sentinel="mcp_output_schema"):
    tool_intent = {
        "name": "container_inspect",
        "description": "Inspect a container.",
        "domain": "container_runtime",
        "operation": "inspect",
        "requires": ["container_id_or_name"],
        "evidence_types": ["runtime_metadata"],
        "risk": "read_only",
        "target_scopes": ["runtime_state"],
        "freshness_support": "live_only",
        "tool_role": "primary",
        "output_schema": sentinel,
        "capability_complete": True,
        "tool_intent_meta": {
            "schema_version": schema_version,
            "source_sha256": "a" * 64,
            "bundle_version": "2.1.0",
        },
    }
    raw = {
        "name": "container_inspect",
        "description": "Inspect a container (live).",
        "tool_intent": tool_intent,
    }
    if output_schema is not _MISSING:
        raw["outputSchema"] = output_schema
    return raw


def test_descriptor_projects_nested_live_output_schema_as_deep_copy():
    live_schema = {
        "type": "object",
        "properties": {"status": {"type": "string", "enum": ["running"]}},
    }

    descriptor = descriptor_from_raw(_raw_tool(live_schema))

    assert descriptor is not None
    assert descriptor.output_schema == live_schema
    assert descriptor.output_schema is not live_schema
    assert descriptor.output_schema["properties"] is not live_schema["properties"]
    live_schema["properties"]["status"]["enum"].append("stopped")
    assert descriptor.output_schema["properties"]["status"]["enum"] == ["running"]


def test_descriptor_keeps_live_schema_separate_from_capability_sentinel():
    descriptor = descriptor_from_raw(_raw_tool({"type": "object"}))

    assert descriptor is not None
    assert descriptor.capability_output_schema == "mcp_output_schema"
    assert descriptor.output_schema == {"type": "object"}


def test_schema_v2_sentinel_without_live_output_schema_is_not_eligible():
    assert descriptor_from_raw(_raw_tool()) is None


def test_schema_v2_sentinel_with_non_mapping_live_output_schema_is_not_eligible():
    assert descriptor_from_raw(_raw_tool([{"type": "object"}])) is None


def test_schema_v2_sentinel_preserves_present_empty_mapping():
    descriptor = descriptor_from_raw(_raw_tool({}))

    assert descriptor is not None
    assert descriptor.output_schema == {}
    assert descriptor.capability_output_schema == "mcp_output_schema"


def test_legacy_v1_without_sentinel_is_not_excluded_by_v2_schema_gate():
    raw = _raw_tool(schema_version=1, sentinel="")
    raw["tool_intent"].pop("capability_complete")

    descriptor = descriptor_from_raw(raw)

    assert descriptor is not None
    assert descriptor.output_schema == {}
    assert descriptor.capability_output_schema == ""


def test_details_by_name_forwards_output_schema_as_deep_copy():
    output_schema = {"type": "object", "properties": {"status": {"type": "string"}}}
    descriptor = ToolDescriptor(
        name="container_inspect",
        capability_output_schema="mcp_output_schema",
        output_schema=output_schema,
    )

    detail = details_by_name([descriptor])["container_inspect"]

    assert detail["output_schema"] == output_schema
    assert detail["output_schema"] is not output_schema
    assert detail["output_schema"]["properties"] is not output_schema["properties"]
    output_schema["properties"]["status"]["type"] = "number"
    assert detail["output_schema"]["properties"]["status"]["type"] == "string"
