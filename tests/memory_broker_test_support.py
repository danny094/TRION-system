from __future__ import annotations

from typing import Any, Dict

from mcp.tool_result_contracts import (
    MCPResultPresence,
    MCPToolCallStatus,
    MCPToolResultEnvelope,
)


def _ok(items: list) -> MCPToolResultEnvelope:
    """Simuliert ein erfolgreiches kanonisches Tool-Result mit Items."""
    return MCPToolResultEnvelope(
        MCPToolCallStatus.SUCCESS,
        structured_content_presence=(
            MCPResultPresence.VALUE if items else MCPResultPresence.EMPTY
        ),
        structured_content={"results": items} if items else {},
    )


def _err(msg: str = "mcp_timeout") -> MCPToolResultEnvelope:
    """Simuliert ein kanonisches Transportfehler-Result."""
    return MCPToolResultEnvelope(
        MCPToolCallStatus.TRANSPORT_FAILURE,
        transport_diagnostic=msg,
    )


def _item(content: str, item_id: int = 1, extra: Dict | None = None) -> Dict[str, Any]:
    base = {"id": item_id, "content": content, "role": "user", "layer": "stm"}
    if extra:
        base.update(extra)
    return base


def _make_call_tool(responses: Dict[str, Any]):
    """Erzeugt einen call_tool-Mock der je nach Tool-Name antwortet."""
    def fake_call_tool(tool_name: str, arguments: Dict, timeout=5.0):
        return responses.get(tool_name, _ok([]))
    return fake_call_tool
