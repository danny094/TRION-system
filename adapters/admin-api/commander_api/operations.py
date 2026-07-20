from fastapi import APIRouter, HTTPException, Request, WebSocket as WS

from commander_approval_store import get_approval, get_history, get_pending
from commander_api.mcp_runtime import (
    export_marketplace_bundle_via_mcp,
    get_dashboard_overview_via_mcp,
    get_proxy_whitelist_via_mcp,
    import_marketplace_bundle_via_mcp,
    install_marketplace_catalog_blueprint_via_mcp,
    install_marketplace_starter_via_mcp,
    list_marketplace_bundles_via_mcp,
    list_marketplace_catalog_via_mcp,
    list_marketplace_starters_via_mcp,
    set_proxy_whitelist_via_mcp,
    start_proxy_via_mcp,
    stop_proxy_via_mcp,
    sync_marketplace_catalog_via_mcp,
)
from commander_approval_workflow import approve, reject
from commander_ws_activity import ws_handler

from .common import exception_response, logger

router = APIRouter()


def _approval_error_meta(message: str) -> tuple[str, int]:
    msg = str(message or "").strip().lower()
    if msg.startswith("healthcheck_timeout_auto_stopped"):
        return "healthcheck_timeout", 504
    if msg.startswith("healthcheck_unhealthy_auto_stopped"):
        return "healthcheck_unhealthy", 409
    if msg.startswith("container_exited_before_ready_auto_stopped"):
        return "container_not_ready", 409
    return "approval_failed", 409


@router.get("/approvals")
async def api_get_pending_approvals():
    """Get all pending approval requests."""
    try:
        pending = get_pending()
        return {"approvals": pending, "count": len(pending)}
    except Exception as e:
        return exception_response(e)


@router.get("/approvals/history")
async def api_approval_history(limit: int = 20):
    """Get approval history including resolved entries."""
    try:
        history = get_history(limit=limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        return exception_response(e)


@router.get("/approvals/{approval_id}")
async def api_get_approval(approval_id: str):
    """Get a specific approval request."""
    try:
        a = get_approval(approval_id)
        if not a:
            return exception_response(
                HTTPException(404, f"Approval '{approval_id}' not found"),
                error_code="not_found",
                details={"approval_id": approval_id},
            )
        return a
    except Exception as e:
        return exception_response(e)


@router.post("/approvals/{approval_id}/approve")
async def api_approve(approval_id: str):
    """Approve a pending request — starts the container."""
    try:
        result = approve(approval_id, approved_by="user")
        if result is None:
            return exception_response(
                HTTPException(404, "Approval not found, expired, or already resolved"),
                error_code="not_found",
                details={"approved": False, "approval_id": approval_id},
            )
        if "error" in result:
            runtime_code, runtime_status = _approval_error_meta(result["error"])
            return exception_response(
                RuntimeError(result["error"]),
                status_code=runtime_status,
                error_code=runtime_code,
                details={"approved": False},
            )
        return {"approved": True, "container": result}
    except Exception as e:
        return exception_response(e)


@router.post("/approvals/{approval_id}/reject")
async def api_reject(approval_id: str, request: Request):
    """Reject a pending approval request."""
    try:
        is_json = request.headers.get("content-type", "").startswith("application/json")
        data = await request.json() if is_json else {}
        reason = data.get("reason", "")
        rejected = reject(approval_id, rejected_by="user", reason=reason)
        if not rejected:
            return exception_response(
                HTTPException(404, "Approval not found or already resolved"),
                error_code="not_found",
                details={"rejected": False, "approval_id": approval_id},
            )
        return {"rejected": True, "approval_id": approval_id}
    except Exception as e:
        return exception_response(e)


@router.websocket("/ws")
async def websocket_terminal(websocket: WS):
    """WebSocket endpoint for live terminal streaming."""
    try:
        await ws_handler(websocket)
    except Exception as e:
        logger.error(f"[Commander] WebSocket error: {e}")


@router.post("/proxy/start")
async def api_start_proxy():
    """Start the Squid whitelist proxy."""
    try:
        ok = start_proxy_via_mcp()
        return {"started": ok}
    except Exception as e:
        return exception_response(e)


@router.post("/proxy/stop")
async def api_stop_proxy():
    """Stop the Squid proxy."""
    try:
        stop_proxy_via_mcp()
        return {"stopped": True}
    except Exception as e:
        return exception_response(e)


@router.get("/proxy/whitelist/{blueprint_id}")
async def api_get_whitelist(blueprint_id: str):
    try:
        domains = get_proxy_whitelist_via_mcp(blueprint_id)
        return {"blueprint_id": blueprint_id, "domains": domains}
    except Exception as e:
        return exception_response(e)


@router.post("/proxy/whitelist/{blueprint_id}")
async def api_set_whitelist(blueprint_id: str, request: Request):
    try:
        data = await request.json()
        domains = data.get("domains", [])
        ok = set_proxy_whitelist_via_mcp(blueprint_id, list(domains) if isinstance(domains, list) else [])
        return {"updated": ok, "blueprint_id": blueprint_id, "domains": domains}
    except Exception as e:
        return exception_response(e)


@router.get("/marketplace/bundles")
async def api_list_bundles():
    try:
        return list_marketplace_bundles_via_mcp()
    except Exception as e:
        return exception_response(e)


@router.get("/marketplace/starters")
async def api_list_starters():
    try:
        return list_marketplace_starters_via_mcp()
    except Exception as e:
        return exception_response(e)


@router.get("/marketplace/catalog")
async def api_marketplace_catalog(category: str = "", trusted_only: bool = False):
    try:
        return list_marketplace_catalog_via_mcp(category=category, trusted_only=trusted_only)
    except Exception as e:
        return exception_response(e)


@router.post("/marketplace/catalog/sync")
async def api_marketplace_catalog_sync(request: Request):
    try:
        data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        repo_url = str((data or {}).get("repo_url", "")).strip()
        branch = str((data or {}).get("branch", "main")).strip() or "main"
        return sync_marketplace_catalog_via_mcp(repo_url=repo_url, branch=branch)
    except Exception as e:
        return exception_response(e, error_code="marketplace_sync_failed")


@router.post("/marketplace/catalog/install/{blueprint_id}")
async def api_marketplace_catalog_install(blueprint_id: str, request: Request):
    try:
        data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        overwrite = bool((data or {}).get("overwrite", False))
        return install_marketplace_catalog_blueprint_via_mcp(blueprint_id=blueprint_id, overwrite=overwrite)
    except Exception as e:
        return exception_response(e, error_code="marketplace_install_failed")


@router.post("/marketplace/starters/{starter_id}/install")
async def api_install_starter(starter_id: str):
    try:
        return install_marketplace_starter_via_mcp(starter_id)
    except Exception as e:
        return exception_response(e)


@router.post("/marketplace/export/{blueprint_id}")
async def api_export_bundle(blueprint_id: str):
    try:
        result = export_marketplace_bundle_via_mcp(blueprint_id)
        filename = str(result.get("filename") or "").strip()
        if not filename:
            return exception_response(
                HTTPException(404, "Blueprint not found"),
                error_code="not_found",
                details={"exported": False, "blueprint_id": blueprint_id},
            )
        return {"exported": True, "filename": filename}
    except Exception as e:
        return exception_response(e)


@router.post("/marketplace/import")
async def api_import_bundle(request: Request):
    try:
        body = await request.body()
        result = import_marketplace_bundle_via_mcp(body)
        if not result:
            return exception_response(RuntimeError("Import failed"), error_code="import_failed")
        return result
    except Exception as e:
        return exception_response(e)


@router.get("/dashboard")
async def api_dashboard():
    """Full system dashboard with health, resources, alerts, events."""
    try:
        return get_dashboard_overview_via_mcp()
    except Exception as e:
        return exception_response(e)
