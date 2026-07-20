"""
Container Commander — REST API Routes (modularized)
════════════════════════════════════════════════════
Main router keeps blueprint lifecycle + deploy path and composes specialized
subrouters from `commander_api/*`.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from commander_container_lifecycle import start_container
from commander_api.mcp_blueprints import (
    create_blueprint_via_mcp,
    delete_blueprint_via_mcp,
    empty_hardware_preview_payload,
    export_blueprint_yaml_via_mcp,
    get_blueprint_via_mcp,
    import_blueprint_yaml_via_mcp,
    list_blueprints_via_mcp,
    update_blueprint_via_mcp,
)
from commander_api.common import exception_response
from commander_runtime_errors import extract_pending_approval
from commander_runtime_models import ResourceLimits

logger = logging.getLogger(__name__)
router = APIRouter()


def _runtime_deploy_error_meta(message: str) -> tuple[str, int]:
    msg = str(message or "").strip().lower()
    if msg.startswith("healthcheck_timeout_auto_stopped"):
        return "healthcheck_timeout", 504
    if msg.startswith("healthcheck_unhealthy_auto_stopped"):
        return "healthcheck_unhealthy", 409
    if msg.startswith("container_exited_before_ready_auto_stopped"):
        return "container_not_ready", 409
    return "deploy_conflict", 409


# ═══════════════════════════════════════════════════════════
# BLUEPRINT ENDPOINTS (kept local: includes tombstone logic)
# ═══════════════════════════════════════════════════════════

@router.get("/blueprints")
async def api_list_blueprints(tag: Optional[str] = None):
    try:
        blueprints = list_blueprints_via_mcp()
        if tag:
            tag_lower = str(tag).strip().lower()
            filtered = []
            for item in blueprints:
                blueprint_id = str(item.get("blueprint_id") or "").strip()
                if not blueprint_id:
                    continue
                detail = get_blueprint_via_mcp(blueprint_id)
                tags = {
                    str(value).strip().lower()
                    for value in list((detail.get("definition") or {}).get("tags") or [])
                    if str(value).strip()
                }
                if tag_lower in tags:
                    filtered.append(detail)
            blueprints = filtered
        return {"blueprints": blueprints, "count": len(blueprints)}
    except Exception as e:
        logger.error(f"[Commander] List blueprints: {e}")
        return exception_response(e)


@router.get("/blueprints/{blueprint_id}")
async def api_get_blueprint(blueprint_id: str, resolve: bool = True, hardware_preview: bool = False):
    try:
        payload = get_blueprint_via_mcp(blueprint_id)
        if hardware_preview:
            # v2 blueprint_get liefert aktuell keine hardware_intents.
            payload["hardware_preview"] = empty_hardware_preview_payload(
                connector="container",
                target_type="blueprint",
                target_id=blueprint_id,
            )
            payload["hardware_preview_error"] = "hardware_preview_unavailable_in_blueprint_read_v2"
        return payload
    except Exception as e:
        return exception_response(e)


@router.post("/blueprints")
async def api_create_blueprint(request: Request):
    try:
        data = await request.json()
        result = create_blueprint_via_mcp(data)
        return {
            "created": True,
            "blueprint": result.get("blueprint", {}),
            "trust": result.get("trust", {}),
            "graph_sync": {"attempted": False, "reason": "graph_sync_not_available_in_v2_mcp"},
        }
    except Exception as e:
        return exception_response(e)


@router.put("/blueprints/{blueprint_id}")
async def api_update_blueprint(blueprint_id: str, request: Request):
    try:
        data = await request.json()
        result = update_blueprint_via_mcp(blueprint_id, data)
        return {
            "updated": True,
            "blueprint": result.get("blueprint", {}),
            "trust": result.get("trust", {}),
            "graph_sync": {"attempted": False, "reason": "graph_sync_not_available_in_v2_mcp"},
        }
    except Exception as e:
        return exception_response(e)


@router.delete("/blueprints/{blueprint_id}")
async def api_delete_blueprint(blueprint_id: str):
    try:
        result = delete_blueprint_via_mcp(blueprint_id)
        if not bool(result.get("deleted")):
            return exception_response(
                HTTPException(404, f"Blueprint '{blueprint_id}' not found"),
                error_code="not_found",
                details={"deleted": False, "blueprint_id": blueprint_id},
            )
        return {
            "deleted": True,
            "blueprint_id": blueprint_id,
            "graph_sync": {"attempted": False, "reason": "graph_sync_not_available_in_v2_mcp"},
        }
    except Exception as e:
        return exception_response(e)


@router.post("/blueprints/import")
async def api_import_blueprint(request: Request):
    try:
        data = await request.json()
        yaml_content = data.get("yaml", "")
        if not yaml_content:
            return exception_response(
                HTTPException(400, "'yaml' field is required"),
                error_code="bad_request",
                details={"imported": False},
            )
        result = import_blueprint_yaml_via_mcp(yaml_content)
        return {
            "imported": True,
            "blueprint": result.get("blueprint", {}),
            "trust": result.get("trust", {}),
            "graph_sync": {"attempted": False, "reason": "graph_sync_not_available_in_v2_mcp"},
        }
    except Exception as e:
        return exception_response(e)


@router.get("/blueprints/{blueprint_id}/yaml")
async def api_export_yaml(blueprint_id: str):
    try:
        result = export_blueprint_yaml_via_mcp(blueprint_id)
        yaml_str = str(result.get("yaml") or "")
        if not yaml_str:
            return exception_response(
                HTTPException(404, f"Blueprint '{blueprint_id}' not found"),
                error_code="not_found",
                details={"blueprint_id": blueprint_id},
            )
        return {"blueprint_id": blueprint_id, "yaml": yaml_str}
    except Exception as e:
        return exception_response(e)


# ═══════════════════════════════════════════════════════════
# CONTAINER DEPLOY (kept local for explicit parity checks)
# ═══════════════════════════════════════════════════════════

@router.post("/containers/deploy")
async def api_deploy_container(request: Request):
    """Deploy a container from a blueprint via Docker Engine."""
    try:
        data = await request.json()
        blueprint_id = data.get("blueprint_id", "")
        if not blueprint_id:
            return exception_response(
                HTTPException(400, "'blueprint_id' is required"),
                error_code="bad_request",
                details={"deployed": False},
            )

        # P6-C: Accept tracking IDs — not silently dropped.
        conversation_id = data.get("conversation_id", "") or ""
        session_id = data.get("session_id", "") or ""
        if conversation_id or session_id:
            logger.debug(
                "[Commander] Deploy blueprint=%s conversation_id=%s session_id=%s",
                blueprint_id, conversation_id or "(none)", session_id or "(none)",
            )

        override = None
        if data.get("override_resources"):
            override = ResourceLimits(**data["override_resources"])
        mount_overrides = data.get("mount_overrides")
        storage_scope_override = data.get("storage_scope_override")
        device_overrides = data.get("device_overrides")
        block_apply_handoff_resource_ids = data.get("block_apply_handoff_resource_ids")

        instance = start_container(
            blueprint_id,
            override,
            data.get("environment"),
            data.get("resume_volume"),
            mount_overrides=mount_overrides,
            storage_scope_override=storage_scope_override,
            device_overrides=device_overrides,
            block_apply_handoff_resource_ids=block_apply_handoff_resource_ids,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        return {
            "deployed": True,
            "container": instance.model_dump(),
            "hardware_deploy": {
                "block_apply_handoff_resource_ids_requested": list(instance.block_apply_handoff_resource_ids_requested or []),
                "block_apply_handoff_resource_ids_applied": list(instance.block_apply_handoff_resource_ids_applied or []),
                "hardware_resolution_preview": dict(instance.hardware_resolution_preview or {}),
            },
        }
    except RuntimeError as e:
        runtime_code, runtime_status = _runtime_deploy_error_meta(str(e))
        return exception_response(
            e,
            status_code=runtime_status,
            error_code=runtime_code,
            details={"deployed": False},
        )
    except ValueError as e:
        return exception_response(
            e,
            status_code=404,
            error_code="not_found",
            details={"deployed": False},
        )
    except Exception as e:
        pending = extract_pending_approval(e)
        if pending is not None:
            return JSONResponse(
                {
                    "deployed": False,
                    "pending_approval": True,
                    "approval_id": pending.approval_id,
                    "reason": pending.reason,
                    "block_apply_handoff_resource_ids_requested": list(block_apply_handoff_resource_ids or []),
                    "conversation_id": conversation_id or None,
                    "session_id": session_id or None,
                },
                status_code=202,
            )
        logger.error(f"[Commander] Deploy: {e}")
        return exception_response(e, details={"deployed": False})


# ═══════════════════════════════════════════════════════════
# COMPOSE MODULAR SUBROUTERS
# ═══════════════════════════════════════════════════════════

from commander_api.secrets import router as secrets_router
from commander_api.containers import router as containers_router
from commander_api.audit import router as audit_router
from commander_api.hardware import router as hardware_router
from commander_api.storage import router as storage_router
from commander_api.operations import router as operations_router
try:
    from trion_memory_routes import router as trion_memory_router
except ModuleNotFoundError as e:
    trion_memory_router = None
    logger.warning("[Commander] trion_memory_routes unavailable (%s) - TRION memory subroutes disabled", e)

router.include_router(secrets_router)
router.include_router(containers_router)
router.include_router(audit_router)
router.include_router(hardware_router)
router.include_router(storage_router)
router.include_router(operations_router)
if trion_memory_router is not None:
    router.include_router(trion_memory_router, prefix="/trion/memory")
