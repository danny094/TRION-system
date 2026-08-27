from __future__ import annotations

from .contracts import ContainerReferenceContractSpec, SourceModuleSpec


def render_tools_module(
    module: SourceModuleSpec,
    reference_contract: ContainerReferenceContractSpec,
) -> str:
    tools = ",\n".join(
        _render_tool(tool, reference_contract) for tool in module.tools
    )
    return f'#!/usr/bin/env python3\nTOOLS_PART = [\n{tools}\n]\n'


def _render_tool(tool, reference_contract: ContainerReferenceContractSpec) -> str:
    reference_schema = (
        reference_contract.input_schema
        if tool.name in reference_contract.tool_names
        else None
    )
    schema_lines = ["        \"type\": \"object\","]
    properties = ",\n".join(
        _render_property(
            param,
            (reference_schema or {}).get("properties", {}).get(param.name),
        )
        for param in tool.parameters
    )
    schema_lines.append("        \"properties\": {" + (f"\n{properties}\n        " if properties else "") + "},")
    required = [param.name for param in tool.parameters if not param.has_default]
    if required:
        req = ", ".join(f'"{name}"' for name in required)
        schema_lines.append(f"        \"required\": [{req}],")
    if reference_schema is not None:
        schema_lines.append(f'        "oneOf": {reference_schema["oneOf"]!r},')
    schema_lines.append("        \"additionalProperties\": False,")
    schema = "\n".join(schema_lines)
    return (
        "    {\n"
        f'        "name": "{tool.name}",\n'
        f'        "description": "{tool.description}",\n'
        "        \"inputSchema\": {\n"
        f"{schema}\n"
        "        },\n"
        f'        "outputSchema": {tool.output_schema!r},\n'
        "    }"
    )


def _render_property(param, schema_override=None) -> str:
    if schema_override is not None:
        return f'            "{param.name}": {schema_override!r}'
    shape = _json_shape(param.annotation)
    keep_default = param.has_default and param.default_repr not in {None, "''", '""'}
    default = f', "default": {param.default_repr}' if keep_default else ""
    if param.annotation == "list[str]":
        return f'            "{param.name}": {{"type": "array", "items": {{"type": "string"}}{default}}}'
    return f'            "{param.name}": {{"type": "{shape}"{default}}}'


def _json_shape(annotation: str | None) -> str:
    if annotation == "int":
        return "integer"
    if annotation == "bool":
        return "boolean"
    if annotation == "dict":
        return "object"
    if annotation == "list[str]":
        return "array"
    return "string"
