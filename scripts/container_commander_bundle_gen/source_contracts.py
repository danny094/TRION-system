from __future__ import annotations

import ast
from pathlib import Path

from .contracts import ContainerReferenceContractSpec, SourceModuleSpec


def load_container_reference_contract(path: Path) -> ContainerReferenceContractSpec:
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    assignments = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    tool_names = ast.literal_eval(assignments["PHASE_1_CONTAINER_REFERENCE_NAMES"])
    input_schema = ast.literal_eval(assignments["CONTAINER_REFERENCE_INPUT_SCHEMA"])
    contract = ContainerReferenceContractSpec(
        tool_names=tuple(tool_names),
        input_schema=input_schema,
        error_source=ast.get_source_segment(
            source, classes["ContainerReferenceError"]
        ) or "",
        normalizer_source=ast.get_source_segment(
            source, functions["normalize_container_reference"]
        ) or "",
    )
    _assert_reference_contract(contract)
    return contract


def assert_contract_bindings(
    modules: tuple[SourceModuleSpec, ...],
    tool_intents: object,
    output_schemas: object,
    reference_contract: ContainerReferenceContractSpec,
) -> None:
    if not isinstance(tool_intents, dict) or tool_intents.get("schema_version") != 2:
        raise ValueError("container commander tool intents must use schema_version 2")
    raw_intents = tool_intents.get("tools")
    if not isinstance(raw_intents, list) or not all(
        isinstance(item, dict) for item in raw_intents
    ):
        raise ValueError("container commander tool intents must contain tool mappings")
    if not isinstance(output_schemas, dict) or not all(
        isinstance(name, str) and isinstance(schema, dict)
        for name, schema in output_schemas.items()
    ):
        raise ValueError("container commander output schemas must be a mapping")
    tools = [tool for module in modules for tool in module.tools]
    source_names = [tool.name for tool in tools]
    intent_names = [str(item.get("name") or "") for item in raw_intents]
    if len(source_names) != len(set(source_names)):
        raise ValueError("container commander source tool names must be unique")
    if intent_names != source_names:
        raise ValueError("container commander tool intents must match source registration order")
    if set(output_schemas) != set(source_names):
        raise ValueError("container commander output schemas must match source tools exactly")
    tools_by_name = {tool.name: tool for tool in tools}
    for tool_name in reference_contract.tool_names:
        tool = tools_by_name.get(tool_name)
        if tool is None:
            raise ValueError(f"container reference tool is not registered: {tool_name}")
        parameters = {parameter.name: parameter for parameter in tool.parameters}
        if set(reference_contract.input_schema["properties"]) - set(parameters):
            raise ValueError(f"container reference signature is incomplete: {tool_name}")
        if any(
            not parameters[name].has_default
            for name in reference_contract.input_schema["properties"]
        ):
            raise ValueError(f"container reference fields must remain optional: {tool_name}")


def _assert_reference_contract(contract: ContainerReferenceContractSpec) -> None:
    if not contract.tool_names or len(contract.tool_names) != len(set(contract.tool_names)):
        raise ValueError("container reference tools must be unique")
    schema = contract.input_schema
    if schema.get("type") != "object" or set(schema.get("properties") or {}) != {
        "container_id",
        "container_name",
    }:
        raise ValueError("container reference schema must expose id and name")
    if not isinstance(schema.get("oneOf"), list) or len(schema["oneOf"]) != 2:
        raise ValueError("container reference schema must encode exactly one reference")
    if not contract.error_source or not contract.normalizer_source:
        raise ValueError("container reference runtime projection source is missing")
