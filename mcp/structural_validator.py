"""Offline JSON Schema validation for canonical MCP structured output."""

from collections.abc import Mapping

from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator
from referencing import Registry
from referencing.exceptions import Unresolvable

from mcp.structural_validation_contracts import (
    MCPStructuralValidationResult,
    MCPStructuralValidationStatus as Status,
)
from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
    project_tool_result_wire_mapping,
)


def validate_structured_output(
    output_schema: object,
    envelope: MCPToolResultEnvelope,
) -> MCPStructuralValidationResult:
    if not isinstance(envelope, MCPToolResultEnvelope):
        raise TypeError("envelope must be MCPToolResultEnvelope")
    if envelope.status is not MCPToolCallStatus.SUCCESS:
        return MCPStructuralValidationResult.from_envelope_failure(envelope)
    if output_schema is None:
        return MCPStructuralValidationResult(Status.OUTPUT_SCHEMA_MISSING, envelope)
    if not isinstance(output_schema, Mapping):
        return MCPStructuralValidationResult(Status.OUTPUT_SCHEMA_MALFORMED, envelope)

    schema = dict(output_schema)
    dialect = schema.get("$schema")
    if dialect is not None and (not isinstance(dialect, str) or not dialect):
        return MCPStructuralValidationResult(Status.OUTPUT_SCHEMA_MALFORMED, envelope)
    if dialect is not None and dialect != Draft202012Validator.META_SCHEMA["$id"]:
        return MCPStructuralValidationResult(Status.OUTPUT_SCHEMA_UNSUPPORTED, envelope)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        return MCPStructuralValidationResult(Status.OUTPUT_SCHEMA_MALFORMED, envelope)

    if envelope.structured_content_presence is MCPResultPresence.MISSING:
        return MCPStructuralValidationResult(Status.STRUCTURED_CONTENT_MISSING, envelope)
    validator = Draft202012Validator(schema, registry=Registry())
    instance = project_tool_result_wire_mapping(envelope)["structuredContent"]
    try:
        mismatch = next(validator.iter_errors(instance), None)
    except Unresolvable:
        return MCPStructuralValidationResult(Status.OUTPUT_SCHEMA_UNSUPPORTED, envelope)
    if mismatch is not None:
        return MCPStructuralValidationResult(Status.INSTANCE_MISMATCH, envelope)
    return MCPStructuralValidationResult(Status.VALID, envelope)
