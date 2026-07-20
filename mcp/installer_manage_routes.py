import shutil
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from mcp.hub import get_hub
from mcp.installer_common import (
    custom_config_path,
    custom_mcp_dir,
    is_installer_owned,
    load_custom_config,
    reload_hub_registry,
    resolve_icon_path,
)
from mcp.installer_manage_config import (
    apply_config_and_registry_update as _apply_config_and_registry_update,
    preserve_runtime_context as _preserve_runtime_context,
    preserve_tool_intents as _preserve_tool_intents,
    validate_manifest_identity as _validate_manifest_identity,
)
from mcp.installer_manifest import normalize_manifest_payload
from mcp.installer_receipt import owned_paths_from_receipt
from mcp.installer_registry import remove_registry_entry

router = APIRouter()


@router.get("/list")
async def list_mcps():
    return {"mcps": get_hub().list_mcps()}


@router.delete("/{name}")
async def delete_mcp(name: str):
    """Reihenfolge bindend (P11.0-Plan, Lifecycle-Invariante Uninstall):
    Mirror entfernen -> Hub reload -> Bundle entfernen. Der Receipt wird
    VOR dem Registry-Write gelesen, weil er im Bundle liegt und das Bundle
    erst als letzter Schritt verschwindet (SP3, Codex Checkpoint 4 Vorlage).

    Loeschung ist fail-closed (Codex Checkpoint 4 P0/P1): `owned_paths`
    aus dem Receipt wird vorab gegen `target` validiert (kein beliebiger
    Pfad), kein `ignore_errors=True` mehr, und Erfolg wird erst gemeldet,
    wenn `target` nachweislich physisch verschwunden ist."""
    if not is_installer_owned(name):
        _raise_missing_or_core(name, "Cannot delete non-installer-owned MCPs")
    target = custom_mcp_dir(name)
    try:
        owned_paths = owned_paths_from_receipt(name, target)
        remove_registry_entry(name)
        reload_hub_registry(get_hub())
        for path in [target, *owned_paths]:
            if path.exists():
                shutil.rmtree(path)
        if target.exists():
            raise RuntimeError(f"Bundle directory still exists after deletion: {target}")
    except Exception as exc:
        raise HTTPException(500, f"Deletion failed: {exc}") from exc
    return {"success": True, "deleted": name}


@router.post("/{name}/toggle")
async def toggle_mcp(name: str):
    if not is_installer_owned(name):
        _raise_missing_or_core(name, "Cannot toggle non-installer-owned MCPs")
    path = custom_config_path(name)
    if not path.exists():
        _raise_missing_or_core(name, "Cannot toggle MCP (manifest not found)")
    config = load_custom_config(name)
    config["enabled"] = not bool(config.get("enabled", True))
    normalized = normalize_manifest_payload(path.name, config)
    _validate_manifest_identity(name, normalized, path.name)
    _preserve_runtime_context(name, normalized)
    _preserve_tool_intents(name, normalized)
    try:
        _apply_config_and_registry_update(name, config, normalized)
        reload_hub_registry(get_hub())
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Toggle failed: {exc}") from exc
    return {"success": True, "enabled": config["enabled"]}


@router.get("/{name}/details")
async def get_mcp_details(name: str):
    hub = get_hub()
    mcp_info = next((m for m in hub.list_mcps() if m.get("name") == name), None)
    if not mcp_info:
        raise HTTPException(404, f"MCP {name} not found")
    return {"mcp": mcp_info, "tools": _tools_for_mcp(hub, name)}


@router.get("/{name}/icon")
async def get_mcp_icon(name: str):
    config = load_custom_config(name)
    icon_path = resolve_icon_path(name, config)
    if icon_path is None:
        raise HTTPException(404, f"Icon for MCP '{name}' not found")
    return FileResponse(icon_path)


@router.get("/{name}/config")
async def get_mcp_config_payload(name: str):
    return {"name": name, "custom": True, "config": load_custom_config(name)}


@router.put("/{name}/config")
async def update_mcp_config_payload(name: str, request: Request):
    payload = await _load_json_payload(request)
    config = payload.get("config")
    if not isinstance(config, dict):
        raise HTTPException(400, "Field 'config' must be a JSON object")
    path = custom_config_path(name)
    manifest_name = path.name
    try:
        normalized = normalize_manifest_payload(manifest_name, config)
        _validate_manifest_identity(name, normalized, manifest_name)
        _preserve_runtime_context(name, normalized)
        _preserve_tool_intents(name, normalized)
        _apply_config_and_registry_update(name, config, normalized)
        reload_hub_registry(get_hub())
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Config update failed: {exc}") from exc
    return {"success": True, "name": name, "config": config}


def _raise_missing_or_core(name: str, core_message: str) -> None:
    known = _known_mcp_names()
    if name in known:
        raise HTTPException(403, core_message)
    raise HTTPException(404, f"MCP '{name}' not found")


def _known_mcp_names() -> set[str]:
    mcps = get_hub().list_mcps() or []
    return {
        str((mcp or {}).get("name", "")).strip()
        for mcp in mcps
        if isinstance(mcp, dict)
    }


def _tools_for_mcp(hub: Any, name: str) -> list[Dict[str, Any]]:
    tools = []
    for tool_name, mcp_name in hub._tools_cache.items():
        if mcp_name != name:
            continue
        tool_def = hub._tool_definitions.get(tool_name, {})
        tools.append(
            {
                "name": tool_name,
                "description": tool_def.get("description", "No description"),
                "inputSchema": tool_def.get("inputSchema", {}),
            }
        )
    return tools


async def _load_json_payload(request: Request) -> Dict[str, Any]:
    try:
        return await request.json()
    except Exception as exc:
        raise HTTPException(400, f"Invalid JSON payload: {exc}") from exc
