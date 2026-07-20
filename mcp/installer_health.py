"""Post-install health projection kept separate from installer storage."""

import asyncio
from typing import Any, Dict


def is_online_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("online"), bool):
            return value["online"]
        if isinstance(value.get("ok"), bool):
            return value["ok"]
        status = value.get("status")
        if isinstance(status, str):
            return status.lower() in {"ok", "healthy", "online", "ready"}
    return bool(value)


async def run_post_install_health_check(
    hub: Any,
    mcp_name: str,
    attempts: int = 8,
    delay_s: float = 0.25,
) -> Dict[str, str]:
    list_mcps = getattr(hub, "list_mcps", None)
    if not callable(list_mcps):
        return {"status": "unknown", "reason": "hub_missing_list_mcps"}

    reason = "mcp_not_listed"
    total_attempts = max(1, int(attempts))
    for idx in range(total_attempts):
        try:
            mcps = list_mcps()
            if not isinstance(mcps, list):
                return {"status": "unknown", "reason": "invalid_list_mcps_payload"}
            entry = next(
                (
                    m for m in mcps
                    if isinstance(m, dict) and m.get("name") == mcp_name
                ),
                None,
            )
            if entry is None:
                reason = "mcp_not_listed"
            elif is_online_flag(entry.get("online")):
                return {"status": "healthy", "reason": "online"}
            else:
                reason = "mcp_listed_offline"
        except Exception as exc:
            reason = f"list_mcps_error:{exc}"
        if idx < total_attempts - 1:
            await asyncio.sleep(delay_s)
    return {"status": "unhealthy", "reason": reason}
