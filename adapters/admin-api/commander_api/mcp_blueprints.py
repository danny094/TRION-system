from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from mcp.client import call_tool
from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)


_DEFAULT_TIMEOUT_S = 5.0

_ERROR_STATUS = {
    "BLUEPRINT_NOT_FOUND": 404,
    "RUNTIME_UNAVAILABLE": 503,
}


def _unwrap_tool_result(tool_name: str, result: Any) -> dict[str, Any]:
    if not isinstance(result, MCPToolResultEnvelope):
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    if result.status is not MCPToolCallStatus.SUCCESS:
        error = None
        if (
            result.status is MCPToolCallStatus.TOOL_FAILURE
            and result.structured_content_presence is MCPResultPresence.VALUE
        ):
            error = result.structured_content.get("error")
        error = error if isinstance(error, Mapping) else {}
        code = str(error.get("code") or "").strip() or "commander_error"
        message = str(error.get("message") or code).strip() or code
        status_code = 503 if result.status is MCPToolCallStatus.TRANSPORT_FAILURE else _ERROR_STATUS.get(code, 502)
        raise HTTPException(status_code=status_code, detail=message)
    if result.structured_content_presence is MCPResultPresence.MISSING:
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    payload = jsonable_encoder(result.structured_content)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail=f"invalid_{tool_name}_result")
    return payload


def call_commander_blueprint_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    result = call_tool(tool_name, arguments or {}, timeout=timeout)
    return _unwrap_tool_result(tool_name, result)


def list_blueprints_via_mcp(*, timeout: float = _DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    result = call_commander_blueprint_tool("blueprint_list", {}, timeout=timeout)
    blueprints = result.get("blueprints")
    return list(blueprints) if isinstance(blueprints, list) else []


def get_blueprint_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    result = call_commander_blueprint_tool(
        "blueprint_get",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )
    blueprint = result.get("blueprint")
    if not isinstance(blueprint, dict):
        raise HTTPException(status_code=502, detail="invalid_blueprint_get_result")
    return blueprint


def create_blueprint_via_mcp(blueprint: dict[str, Any], *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_blueprint_tool("blueprint_create", {"blueprint": blueprint}, timeout=timeout)


def update_blueprint_via_mcp(
    blueprint_id: str,
    updates: dict[str, Any],
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    return call_commander_blueprint_tool(
        "blueprint_update",
        {"blueprint_id": blueprint_id, "updates": updates},
        timeout=timeout,
    )


def delete_blueprint_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_blueprint_tool(
        "blueprint_delete",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )


def import_blueprint_yaml_via_mcp(yaml_content: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_blueprint_tool("blueprint_import_yaml", {"yaml": yaml_content}, timeout=timeout)


def export_blueprint_yaml_via_mcp(blueprint_id: str, *, timeout: float = _DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    return call_commander_blueprint_tool(
        "blueprint_export_yaml",
        {"blueprint_id": blueprint_id},
        timeout=timeout,
    )


def empty_hardware_preview_payload(
    *,
    connector: str = "container",
    target_type: str = "blueprint",
    target_id: str = "",
) -> dict[str, Any]:
    return {
        "available": False,
        "connector": connector,
        "target_type": target_type,
        "target_id": str(target_id or "").strip(),
        "summary": {
            "supported": False,
            "resolved_count": 0,
            "requires_restart": False,
            "requires_approval": False,
            "device_override_count": 0,
            "mount_override_count": 0,
            "block_candidate_resource_ids": [],
            "container_plan_resource_ids": [],
            "engine_handoff_resource_ids": [],
            "block_apply_handoff_resource_ids_hint": [],
            "engine_opt_in_available": False,
            "unresolved_resource_ids": [],
            "warnings": [],
        },
        "resolution": None,
    }
