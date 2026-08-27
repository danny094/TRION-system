from __future__ import annotations

from typing import Any, Dict, List, Optional

from commander_runtime_connection_inference import infer_access_link_meta, infer_service_name
from commander_runtime_connection_projection import build_connection_info, extract_port_details
from mcp.tool_result_contracts import MCPResultPresence, MCPToolCallStatus, MCPToolResultEnvelope


def merge_host_companion_access_info(
    blueprint_id: str,
    ip_address: Optional[str],
    ports: List[Dict[str, str]],
) -> tuple[List[Dict[str, str]], Dict[str, Any]]:
    connection = build_connection_info(ip_address, ports)

    try:
        from mcp.client import call_tool

        result = call_tool(
            "host_companion_check",
            {"blueprint_id": blueprint_id},
            timeout=5.0,
        )
        if (
            isinstance(result, MCPToolResultEnvelope)
            and result.status is MCPToolCallStatus.SUCCESS
            and result.structured_content_presence is MCPResultPresence.VALUE
            and bool(result.structured_content.get("configured"))
        ):
            host_paths = list(result.structured_content.get("host_paths") or [])
            if host_paths:
                connection["host_companion"] = {
                    "configured": True,
                    "paths": host_paths,
                }
    except Exception:
        pass

    return ports, connection
