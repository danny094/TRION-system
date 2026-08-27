#!/usr/bin/env python3
import inspect
from typing import get_origin

import bundle_docker
from bundle_common import resolve_container_reference
import bundle_generated_runtime as generated_runtime
import bundle_tools_runtime as tools_runtime
import bundle_generated_runtime_actions_cleanup as generated_runtime_actions_cleanup
import bundle_tools_runtime_actions_cleanup as tools_runtime_actions_cleanup
import bundle_generated_blueprints as generated_blueprints
import bundle_tools_blueprints as tools_blueprints
import bundle_generated_network as generated_network
import bundle_tools_network as tools_network
import bundle_generated_dashboard as generated_dashboard
import bundle_tools_dashboard as tools_dashboard
import bundle_generated_host_companion as generated_host_companion
import bundle_tools_host_companion as tools_host_companion
import bundle_generated_marketplace as generated_marketplace
import bundle_tools_marketplace as tools_marketplace
import bundle_generated_volumes as generated_volumes
import bundle_tools_volumes as tools_volumes
import bundle_generated_runtime_actions_lifecycle as generated_runtime_actions_lifecycle
import bundle_tools_runtime_actions_lifecycle as tools_runtime_actions_lifecycle

MCP_PROTOCOL_VERSION = "2024-11-05"
TOOL_MODULES = (generated_runtime, generated_runtime_actions_cleanup, generated_blueprints, generated_network, generated_dashboard, generated_host_companion, generated_marketplace, generated_volumes, generated_runtime_actions_lifecycle,)
TOOLS = tools_runtime.TOOLS_PART + tools_runtime_actions_cleanup.TOOLS_PART + tools_blueprints.TOOLS_PART + tools_network.TOOLS_PART + tools_dashboard.TOOLS_PART + tools_host_companion.TOOLS_PART + tools_marketplace.TOOLS_PART + tools_volumes.TOOLS_PART + tools_runtime_actions_lifecycle.TOOLS_PART

class ContainerReferenceError(ValueError):
    pass


def normalize_container_reference(
    container_id: str = "",
    container_name: str = "",
) -> tuple[str, str]:
    normalized_id = str(container_id or "").strip()
    normalized_name = str(container_name or "").strip()
    if bool(normalized_id) == bool(normalized_name):
        raise ContainerReferenceError(
            "Provide exactly one of container_id or container_name"
        )
    if normalized_id:
        return "container_id", normalized_id
    return "container_name", normalized_name


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
        return value or {}
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
        return None, {"code": -32602, "message": str(exc)}
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
    return {"content": [], "structuredContent": result, "isError": is_error}


def handle_request(payload):
    method = payload.get("method", "")
    request_id = payload.get("id")
    params = payload.get("params") or {}
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": MCP_PROTOCOL_VERSION, "serverInfo": {"name": "container-commander", "version": "2.1.0"}, "capabilities": {"tools": {"listChanged": False}}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method != "tools/call":
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    name = str((params.get("name") or "")).strip()
    arguments = params.get("arguments") or {}
    tool = _find_tool(name)
    if tool is None:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
    signature = inspect.signature(tool)
    kwargs = {}
    has_container_guard = {"container_id", "container_name"}.issubset(signature.parameters)
    if has_container_guard:
        container_id, error = _normalize_container_arguments(arguments)
        if error is not None:
            return {"jsonrpc": "2.0", "id": request_id, "error": error}
        kwargs["container_id"] = container_id
    for param in signature.parameters.values():
        if param.name in {"container_id", "container_name"} and has_container_guard:
            continue
        if param.name in arguments:
            kwargs[param.name] = _coerce(arguments.get(param.name), param.annotation)
        elif param.default is inspect._empty:
            kwargs[param.name] = _coerce(None, param.annotation)
    try:
        result = _project_tool_result(tool(**kwargs))
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(exc) or "Tool execution failed"}}
    if result is None:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": "Tool result must be an object"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}
