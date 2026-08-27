from __future__ import annotations

from copy import deepcopy
import importlib.util
import inspect
import json
from pathlib import Path

import pytest
from jsonschema.validators import Draft202012Validator

import container_commander_bundle_fakes  # noqa: F401
import bundle_dispatch
from mcp.protocol_contracts import MCPTransportRequestOutcome, MCPTransportRequestStatus
from mcp.structural_validation_contracts import MCPStructuralValidationStatus
from mcp.structural_validator import validate_structured_output
from mcp.tool_result_contracts import project_tool_result_envelope


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "mcp-servers" / "container-commander"
PHASE_1_REFERENCE_TOOLS = ("container_inspect", "container_logs")
OUTPUT_REQUIRED = {
    "container_list": {
        "container_id", "name", "image", "status", "created_at",
        "managed_by_trion", "actions_allowed", "protected",
    },
    "container_inspect": {
        "container_id", "name", "image", "status", "created_at",
        "managed_by_trion", "actions_allowed", "protected", "blueprint_id",
        "labels", "ports", "mounts", "runtime_state", "home_scope",
    },
    "blueprint_list": {"blueprint_id", "name", "description", "version"},
    "blueprint_get": {
        "blueprint_id", "name", "description", "version", "definition",
    },
}


def _source_contracts():
    path = SOURCE_ROOT / "contracts.py"
    spec = importlib.util.spec_from_file_location("commander_source_contracts", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tool(tool_name):
    return next(tool for tool in bundle_dispatch.TOOLS if tool["name"] == tool_name)


def _valid_reference_payloads():
    return (
        {"container_id": "c1"},
        {"container_name": "demo"},
        {"container_id": "c1", "container_name": ""},
        {"container_id": "", "container_name": "demo"},
        {"container_id": " c1 ", "container_name": "\t"},
        {"container_id": "  ", "container_name": " demo "},
    )


def _invalid_reference_payloads():
    return (
        {},
        {"container_id": ""},
        {"container_name": ""},
        {"container_id": "  "},
        {"container_name": "\t"},
        {"container_id": "", "container_name": ""},
        {"container_id": " ", "container_name": "\t"},
        {"container_id": "c1", "container_name": "demo"},
    )


def test_source_contract_is_the_single_exactly_one_owner():
    contracts = _source_contracts()
    schema = getattr(contracts, "CONTAINER_REFERENCE_INPUT_SCHEMA", None)
    tools = getattr(contracts, "PHASE_1_CONTAINER_REFERENCE_NAMES", None)
    normalize = getattr(contracts, "normalize_container_reference", None)
    error_type = getattr(contracts, "ContainerReferenceError", None)

    assert isinstance(schema, dict)
    assert tools == PHASE_1_REFERENCE_TOOLS
    assert callable(normalize)
    assert isinstance(error_type, type)
    assert normalize(container_id="c1") == ("container_id", "c1")
    assert normalize(container_name="demo") == ("container_name", "demo")
    for payload in _invalid_reference_payloads():
        with pytest.raises(error_type):
            normalize(**payload)


def test_phase1_live_input_schemas_project_the_source_xor_contract():
    source_schema = _source_contracts().CONTAINER_REFERENCE_INPUT_SCHEMA
    for tool_name in PHASE_1_REFERENCE_TOOLS:
        schema = _tool(tool_name)["inputSchema"]
        for payload in _valid_reference_payloads():
            assert Draft202012Validator(schema).is_valid(payload), (tool_name, payload)
        for payload in _invalid_reference_payloads():
            assert not Draft202012Validator(schema).is_valid(payload), (tool_name, payload)
        assert schema["oneOf"] == source_schema["oneOf"]
        for name, shape in source_schema["properties"].items():
            assert schema["properties"][name] == shape


def test_bundle_dispatch_projects_normalizer_without_a_second_xor_decision():
    contracts = _source_contracts()
    assert inspect.getsource(bundle_dispatch.normalize_container_reference) == inspect.getsource(
        contracts.normalize_container_reference
    )
    dispatcher_source = inspect.getsource(bundle_dispatch._normalize_container_arguments)
    assert "normalize_container_reference(" in dispatcher_source
    assert "bool(container_id) == bool(container_name)" not in dispatcher_source


def _required_fields(tool_name, schema):
    if tool_name == "container_list":
        return set(schema["properties"]["containers"]["items"]["required"])
    if tool_name == "container_inspect":
        return set(schema["properties"]["container"]["required"])
    if tool_name == "blueprint_list":
        return set(schema["properties"]["blueprints"]["items"]["required"])
    return set(schema["properties"]["blueprint"]["required"])


def test_phase1_output_schemas_require_every_doc24_minimum_field():
    schemas = json.loads((SOURCE_ROOT / "output_schemas.json").read_text(encoding="utf-8"))
    for tool_name, required in OUTPUT_REQUIRED.items():
        assert _required_fields(tool_name, schemas[tool_name]) == required
        assert _tool(tool_name)["outputSchema"] == schemas[tool_name]


def _samples():
    summary = {
        "container_id": "c1", "name": "demo", "image": "demo:latest",
        "status": "running", "created_at": "2026-08-24T00:00:00Z",
        "managed_by_trion": True, "actions_allowed": False, "protected": True,
    }
    blueprint = {
        "blueprint_id": "demo", "name": "Demo", "description": "Example",
        "version": "1",
    }
    return {
        "container_list": ({"containers": [summary]}, ("containers", 0)),
        "container_inspect": ({"container": {
            **summary, "blueprint_id": "demo", "labels": {}, "ports": [],
            "mounts": [], "runtime_state": {}, "home_scope": {},
        }}, ("container",)),
        "blueprint_list": ({"blueprints": [blueprint]}, ("blueprints", 0)),
        "blueprint_get": ({"blueprint": {**blueprint, "definition": {}}}, ("blueprint",)),
    }


def _without(payload, path, field):
    candidate = deepcopy(payload)
    target = candidate
    for part in path:
        target = target[part]
    del target[field]
    return candidate


def _validation_status(tool_name, payload):
    envelope = project_tool_result_envelope(MCPTransportRequestOutcome(
        MCPTransportRequestStatus.OK,
        payload={"content": [], "structuredContent": payload, "isError": False},
    ))
    return validate_structured_output(_tool(tool_name)["outputSchema"], envelope).status


def test_p13_validator_rejects_each_missing_doc24_minimum_field():
    for tool_name, (payload, path) in _samples().items():
        assert _validation_status(tool_name, payload) is MCPStructuralValidationStatus.VALID
        for field in OUTPUT_REQUIRED[tool_name]:
            assert _validation_status(
                tool_name, _without(payload, path, field)
            ) is MCPStructuralValidationStatus.INSTANCE_MISMATCH
