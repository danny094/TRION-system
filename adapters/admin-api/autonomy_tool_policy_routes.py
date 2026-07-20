"""
adapters.admin-api.autonomy_tool_policy_routes
===============================================
GET/POST /api/settings/autonomy/tool-policy

Allowlist, Blocklist und Approval-Required-Tools für autonome Ausführung.
Antwortformat analog zu /sequential/runtime — jeder Wert mit value + source.
"""
import os
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from utils.settings import settings
from config.autonomy.tool_policy import (
    get_autonomy_tool_allowlist,
    get_autonomy_tool_blocklist,
    get_autonomy_approval_required_tools,
)

router = APIRouter(tags=["settings"])

_POLICY_KEYS = (
    "AUTONOMY_TOOL_ALLOWLIST",
    "AUTONOMY_TOOL_BLOCKLIST",
    "AUTONOMY_APPROVAL_REQUIRED_TOOLS",
)

_POLICY_GETTERS = {
    "AUTONOMY_TOOL_ALLOWLIST": get_autonomy_tool_allowlist,
    "AUTONOMY_TOOL_BLOCKLIST": get_autonomy_tool_blocklist,
    "AUTONOMY_APPROVAL_REQUIRED_TOOLS": get_autonomy_approval_required_tools,
}


def _source_for(key: str) -> str:
    if key in settings.settings:
        return "override"
    if os.getenv(key, "").strip():
        return "env"
    return "default"


class ToolPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    AUTONOMY_TOOL_ALLOWLIST: Optional[list[str]] = None
    AUTONOMY_TOOL_BLOCKLIST: Optional[list[str]] = None
    AUTONOMY_APPROVAL_REQUIRED_TOOLS: Optional[list[str]] = None


@router.get("/api/settings/autonomy/tool-policy")
async def get_tool_policy():
    """
    Effective autonomy tool policy with source tracking.

    Response shape:
      {
        "effective": {
          "AUTONOMY_TOOL_ALLOWLIST": {"value": [], "source": "default"},
          "AUTONOMY_TOOL_BLOCKLIST": {"value": ["risky_tool"], "source": "env"},
          "AUTONOMY_APPROVAL_REQUIRED_TOOLS": {"value": ["deploy_container"], "source": "override"}
        },
        "defaults": {"AUTONOMY_TOOL_ALLOWLIST": [], ...}
      }
    """
    effective: Dict[str, Any] = {
        key: {"value": _POLICY_GETTERS[key](), "source": _source_for(key)}
        for key in _POLICY_KEYS
    }
    return {
        "effective": effective,
        "defaults": {k: [] for k in _POLICY_KEYS},
    }


@router.post("/api/settings/autonomy/tool-policy")
async def update_tool_policy(update: ToolPolicyUpdate):
    """
    Persist autonomy tool policy overrides.
    Lists are stored as comma-joined strings, compatible with ENV parsing in tool_policy.py.
    Empty list clears the key (falls back to env/default).
    """
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=422, detail="No valid fields provided")

    saved: Dict[str, Any] = {}
    for key, value in payload.items():
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        settings.set(key, ",".join(cleaned))
        saved[key] = cleaned

    return {"success": True, "saved": saved}
