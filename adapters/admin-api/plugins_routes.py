from pathlib import Path
from typing import Any

import httpx
from fastapi import Body
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from config.infra.security import ADMIN_CSRF_HEADER_NAME
from mcp.installer_common import InstallationError, MAX_SIZE
from mcp.catalog_lifecycle import current_catalog_snapshot
from plugins.common import load_plugin_manifest, resolve_plugin_asset
from plugins.bridge import call_permitted_tool, proxy_request
from plugins.install import cleanup_failed_install, install_plugin_bundle
from plugins.storage import list_plugins, plugin_exists, remove_plugin, write_enabled

router = APIRouter(prefix="/api/plugins", tags=["plugins"])
PLUGIN_ASSET_HEADERS = {
    "Content-Security-Policy": "sandbox allow-scripts allow-forms allow-downloads",
    "X-Content-Type-Options": "nosniff",
}
CSRF_HEADER_PLACEHOLDER = "__TRION_CSRF_HEADER_NAME__"


@router.get("/installed")
async def get_installed_plugins() -> dict[str, Any]:
    return {"plugins": list_plugins()}


@router.get("/runtime/bridge.js")
async def get_plugin_bridge_script():
    script_path = Path(__file__).resolve().parents[2] / "plugins" / "runtime_bridge.js"
    source = script_path.read_text(encoding="utf-8")
    if source.count(CSRF_HEADER_PLACEHOLDER) != 1:
        raise RuntimeError("Plugin runtime bridge CSRF placeholder is invalid")
    return Response(
        content=source.replace(CSRF_HEADER_PLACEHOLDER, ADMIN_CSRF_HEADER_NAME),
        media_type="application/javascript",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/install")
async def install_plugin(request: Request, file: Any = None) -> dict[str, Any]:
    try:
        upload = await _resolve_upload(file=file, request=request)
        content = await upload.read()
        if len(content) > MAX_SIZE:
            raise HTTPException(400, "File too large (max 50MB)")
        snapshot = current_catalog_snapshot()
        installed_mcps = set(snapshot.desired_mcps) if snapshot is not None else set()
        manifest = install_plugin_bundle(upload.filename, content, installed_mcps)
        return {"success": True, "plugin": {**manifest, "missing_mcp": []}}
    except InstallationError as exc:
        cleanup_failed_install(locals().get("manifest", {}).get("id"), None)
        raise HTTPException(400, exc.message) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Plugin installation failed: {exc}") from exc


@router.get("/{plugin_id}/manifest")
async def get_plugin_manifest(plugin_id: str) -> dict[str, Any]:
    if not plugin_exists(plugin_id):
        raise HTTPException(404, "Plugin not found")
    return load_plugin_manifest(plugin_id)


@router.get("/{plugin_id}/asset/{asset_path:path}")
async def get_plugin_asset(plugin_id: str, asset_path: str):
    if not plugin_exists(plugin_id):
        raise HTTPException(404, "Plugin not found")
    asset = resolve_plugin_asset(plugin_id, asset_path)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    return FileResponse(asset, headers=PLUGIN_ASSET_HEADERS)


@router.post("/{plugin_id}/bridge/request")
async def bridge_plugin_request(
    plugin_id: str,
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
):
    manifest = _require_plugin_manifest(plugin_id)
    try:
        trusted_headers = request.state.auth_delegation_headers
    except AttributeError as exc:
        raise HTTPException(403, "Verified plugin delegation is required") from exc
    if not isinstance(trusted_headers, dict):
        raise HTTPException(403, "Verified plugin delegation is required")
    try:
        upstream = await proxy_request(manifest, payload, trusted_headers)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Plugin bridge upstream failed: {exc}") from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@router.post("/{plugin_id}/bridge/tools/{tool_name}")
async def bridge_plugin_tool(
    plugin_id: str,
    tool_name: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    manifest = _require_plugin_manifest(plugin_id)
    try:
        result = call_permitted_tool(manifest, tool_name, _tool_args(payload))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    if result.get("error"):
        raise HTTPException(502, result["error"])
    return result


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict[str, Any]:
    return _set_enabled(plugin_id, True)


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict[str, Any]:
    return _set_enabled(plugin_id, False)


@router.delete("/{plugin_id}")
async def delete_plugin(plugin_id: str) -> dict[str, Any]:
    if not plugin_exists(plugin_id):
        raise HTTPException(404, "Plugin not found")
    remove_plugin(plugin_id)
    return {"success": True, "deleted": plugin_id}


def _set_enabled(plugin_id: str, enabled: bool) -> dict[str, Any]:
    if not plugin_exists(plugin_id):
        raise HTTPException(404, "Plugin not found")
    write_enabled(plugin_id, enabled)
    return {"success": True, "plugin_id": plugin_id, "enabled": enabled}


async def _resolve_upload(file: Any, request: Request | None) -> Any:
    if file is not None:
        return file
    if request is None:
        raise HTTPException(400, "No file upload provided")
    form = await request.form()
    upload = form.get("file")
    if upload is None:
        raise HTTPException(400, "No file upload provided")
    return upload


def _require_plugin_manifest(plugin_id: str) -> dict[str, Any]:
    if not plugin_exists(plugin_id):
        raise HTTPException(404, "Plugin not found")
    return load_plugin_manifest(plugin_id)


def _tool_args(payload: dict[str, Any]) -> dict[str, Any]:
    args = payload.get("args") or {}
    if not isinstance(args, dict):
        raise HTTPException(400, "Tool bridge args must be an object")
    return args
