"""
Tools Routes — MCP Hub tool and server listing.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils.logger import log_error
from config.autonomy.tool_policy import (
    get_autonomy_tool_allowlist,
    get_autonomy_tool_blocklist,
    get_autonomy_approval_required_tools,
)

router = APIRouter()


@router.get("/api/tools")
async def tools():
    from mcp.hub import get_hub
    try:
        hub = get_hub()
        hub.initialize()
        mcps = hub.list_mcps() or []
        tool_list = hub.list_tools() or []
        normalized_mcps = [
            {
                "name": str(m.get("name", "")),
                "online": bool(m.get("online")),
                "transport": str(m.get("transport", "")),
                "tools_count": int(m.get("tools_count", 0) or 0),
                "description": str(m.get("description", "")),
                "enabled": bool(m.get("enabled")),
                "url": str(m.get("url", "")),
            }
            for m in mcps if isinstance(m, dict)
        ]
        normalized_tools = [
            {
                "name": str(t.get("name", "")),
                "description": str(t.get("description", "")),
                "mcp_name": hub.get_mcp_for_tool(str(t.get("name", ""))) or "unknown",
                "inputSchema": t.get("inputSchema", {}) if isinstance(t.get("inputSchema"), dict) else {},
            }
            for t in tool_list if isinstance(t, dict) and t.get("name")
        ]
        normalized_mcps.sort(key=lambda x: x.get("name", ""))
        normalized_tools.sort(key=lambda x: x.get("name", ""))
        return JSONResponse({
            "total_tools": len(normalized_tools),
            "total_mcps": len(normalized_mcps),
            "mcps": normalized_mcps,
            "tools": normalized_tools,
        })
    except Exception as e:
        log_error(f"[Tools] Error: {e}")
        return JSONResponse({"total_tools": 0, "total_mcps": 0, "mcps": [], "tools": [], "error": str(e)}, status_code=500)


@router.get("/api/tools/available")
async def tools_available():
    """
    Policy-enriched live list of all MCP tools currently reachable via the hub.
    Each tool includes blocked and approval_required flags derived from the active
    autonomy tool policy (AUTONOMY_TOOL_ALLOWLIST / _BLOCKLIST / _APPROVAL_REQUIRED_TOOLS).
    """
    try:
        from mcp.hub import get_hub
        hub = get_hub()
        hub.initialize()
        tool_list = hub.list_tools() or []

        allowlist = get_autonomy_tool_allowlist()
        blocklist = get_autonomy_tool_blocklist()
        approval_required_tools = get_autonomy_approval_required_tools()

        allowlist_set = set(allowlist)
        blocklist_set = set(blocklist)
        approval_set = set(approval_required_tools)

        enriched = []
        for t in tool_list:
            if not isinstance(t, dict) or not t.get("name"):
                continue
            name = str(t["name"])
            blocked = (bool(allowlist_set) and name not in allowlist_set) or name in blocklist_set
            enriched.append({
                "name": name,
                "description": str(t.get("description", "")),
                "mcp_server": hub.get_mcp_for_tool(name) or "unknown",
                "blocked": blocked,
                "approval_required": name in approval_set,
            })

        enriched.sort(key=lambda x: x["name"])
        return JSONResponse({
            "total_tools": len(enriched),
            "tools": enriched,
            "policy": {
                "allowlist": allowlist,
                "blocklist": blocklist,
                "approval_required_tools": approval_required_tools,
            },
        })
    except Exception as e:
        log_error(f"[Tools/Available] Error: {e}")
        return JSONResponse({"total_tools": 0, "tools": [], "error": str(e)}, status_code=500)
