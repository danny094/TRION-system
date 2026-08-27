from __future__ import annotations

import json

from project_mcp_protocol_version import read_protocol_version_literal

from .contracts import BuildContext


def render_dispatch(context: BuildContext) -> str:
    imports = "\n".join(
        f"import bundle_generated_{module.output_name} as generated_{module.output_name}\n"
        f"import bundle_tools_{module.output_name} as tools_{module.output_name}"
        for module in context.modules
    )
    tool_parts = " + ".join(
        f"tools_{module.output_name}.TOOLS_PART" for module in context.modules
    )
    modules = ", ".join(
        f"generated_{module.output_name}" for module in context.modules
    )
    server = json.dumps(context.metadata["server_info"], ensure_ascii=False)
    version = json.dumps(
        read_protocol_version_literal(
            context.root / "mcp" / "protocol_negotiation_contracts.py"
        )
    )
    contract = context.container_reference_contract
    return _dispatch_source(
        imports,
        tool_parts,
        modules,
        server,
        version,
        contract.error_source,
        contract.normalizer_source,
    )


def _dispatch_source(
    imports: str,
    tool_parts: str,
    modules: str,
    server: str,
    version: str,
    reference_error_source: str,
    reference_normalizer_source: str,
) -> str:
    return f'''#!/usr/bin/env python3
import inspect
from typing import get_origin

import bundle_docker
from bundle_common import resolve_container_reference
{imports}

MCP_PROTOCOL_VERSION = {version}
TOOL_MODULES = ({modules},)
TOOLS = {tool_parts}

{reference_error_source}


{reference_normalizer_source}


def _find_tool(name):
    for module in TOOL_MODULES:
        tool = getattr(module, name, None)
        if callable(tool):
            return tool
    return None


def _coerce(value, annotation):
    origin = get_origin(annotation)
    if annotation is int:
        return int(value or 0)
    if annotation is bool:
        return bool(value)
    if annotation is dict:
        return value or {{}}
    if annotation is list or origin is list:
        return value or []
    return str(value or "")


def _normalize_container_arguments(arguments):
    try:
        reference_kind, container_ref = normalize_container_reference(
            container_id=arguments.get("container_id"),
            container_name=arguments.get("container_name"),
        )
    except ContainerReferenceError as exc:
        return None, {{"code": -32602, "message": str(exc)}}
    if reference_kind == "container_id":
        return container_ref, None
    container = resolve_container_reference(
        bundle_docker.get_docker_client(), container_ref
    )
    return str(getattr(container, "id", "") or container_ref), None


def _project_tool_result(result):
    if not isinstance(result, dict):
        return None
    is_error = result.get("ok") is False and isinstance(result.get("error"), dict)
    return {{"content": [], "structuredContent": result, "isError": is_error}}


def handle_request(payload):
    method = payload.get("method", "")
    request_id = payload.get("id")
    params = payload.get("params") or {{}}
    if method == "initialize":
        return {{"jsonrpc": "2.0", "id": request_id, "result": {{"protocolVersion": MCP_PROTOCOL_VERSION, "serverInfo": {server}, "capabilities": {{"tools": {{"listChanged": False}}}}}}}}
    if method == "tools/list":
        return {{"jsonrpc": "2.0", "id": request_id, "result": {{"tools": TOOLS}}}}
    if method != "tools/call":
        return {{"jsonrpc": "2.0", "id": request_id, "error": {{"code": -32601, "message": f"Method not found: {{method}}"}}}}
    name = str((params.get("name") or "")).strip()
    arguments = params.get("arguments") or {{}}
    tool = _find_tool(name)
    if tool is None:
        return {{"jsonrpc": "2.0", "id": request_id, "error": {{"code": -32601, "message": f"Unknown tool: {{name}}"}}}}
    signature = inspect.signature(tool)
    kwargs = {{}}
    has_container_guard = {{"container_id", "container_name"}}.issubset(signature.parameters)
    if has_container_guard:
        container_id, error = _normalize_container_arguments(arguments)
        if error is not None:
            return {{"jsonrpc": "2.0", "id": request_id, "error": error}}
        kwargs["container_id"] = container_id
    for param in signature.parameters.values():
        if param.name in {{"container_id", "container_name"}} and has_container_guard:
            continue
        if param.name in arguments:
            kwargs[param.name] = _coerce(arguments.get(param.name), param.annotation)
        elif param.default is inspect._empty:
            kwargs[param.name] = _coerce(None, param.annotation)
    try:
        result = _project_tool_result(tool(**kwargs))
    except Exception as exc:
        return {{"jsonrpc": "2.0", "id": request_id, "error": {{"code": -32603, "message": str(exc) or "Tool execution failed"}}}}
    if result is None:
        return {{"jsonrpc": "2.0", "id": request_id, "error": {{"code": -32603, "message": "Tool result must be an object"}}}}
    return {{"jsonrpc": "2.0", "id": request_id, "result": result}}
'''
