from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from mcp.tool_result_contracts import MCPResultPresence, MCPToolCallStatus, MCPToolResultEnvelope


async def _hub_call_tool(tool_name: str, args: dict[str, Any]) -> MCPToolResultEnvelope:
    from mcp.hub import get_hub

    hub = get_hub()
    hub.initialize()
    return await asyncio.to_thread(hub.call_tool, tool_name, args)


def _extract_events(result: MCPToolResultEnvelope) -> list[dict[str, Any]]:
    if not isinstance(result, MCPToolResultEnvelope) or result.status is not MCPToolCallStatus.SUCCESS:
        return []
    structured = jsonable_encoder(result.structured_content)
    payload = structured.get("events") if isinstance(structured, dict) else None
    if payload is None and result.content_presence is not MCPResultPresence.MISSING:
        payload = jsonable_encoder(result.content)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _compact_event_line(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type") or event.get("type") or "").strip()
    event_data = event.get("event_data")
    if not isinstance(event_data, dict):
        event_data = {}
    if event_type == "trion_shell_checkpoint":
        goal = str(event_data.get("goal") or "").strip()
        finding = str(event_data.get("finding") or "").strip()
        action_taken = str(event_data.get("action_taken") or "").strip()
        blocker = str(event_data.get("blocker") or "").strip()
        parts = [part for part in [goal, finding, action_taken, blocker] if part]
        return f"checkpoint: {' | '.join(parts)}".strip()
    if event_type in {"trion_shell_session_summary", "trion_shell_summary"}:
        goal = str(event_data.get("goal") or "").strip()
        summary = str(event_data.get("raw_summary") or event_data.get("summary") or event_data.get("content") or "").strip()
        parts = [part for part in [goal, summary] if part]
        return f"summary: {' | '.join(parts)}".strip()
    content = str(event_data.get("content") or "").strip()
    if content:
        return f"{event_type}: {content}".strip(": ")
    return event_type


async def build_mission_state(conversation_id: str, *, limit: int = 12) -> str:
    conversation = str(conversation_id or "").strip()
    if not conversation or conversation == "global":
        return ""
    result = await _hub_call_tool(
        "workspace_event_list",
        {
            "conversation_id": conversation,
            "limit": max(1, int(limit)),
        },
    )
    events = _extract_events(result)
    relevant = []
    for event in events:
        event_type = str(event.get("event_type") or event.get("type") or "").strip()
        if event_type in {"trion_shell_checkpoint", "trion_shell_session_summary", "trion_shell_summary"}:
            line = _compact_event_line(event)
            if line:
                relevant.append(line)
    if not relevant:
        return ""
    return "\n".join(reversed(relevant[-limit:]))


async def save_shell_checkpoint(
    *,
    conversation_id: str,
    container_id: str,
    blueprint_id: str,
    goal: str,
    finding: str,
    action_taken: str,
    blocker: str,
    step_count: int,
    raw_summary: str = "",
) -> None:
    conversation = str(conversation_id or "").strip()
    if not conversation or conversation == "global":
        return
    await _hub_call_tool(
        "workspace_event_save",
        {
            "conversation_id": conversation,
            "event_type": "trion_shell_checkpoint",
            "event_data": {
                "container_id": str(container_id or "").strip(),
                "blueprint_id": str(blueprint_id or "").strip(),
                "goal": str(goal or "").strip(),
                "finding": str(finding or "").strip(),
                "action_taken": str(action_taken or "").strip(),
                "blocker": str(blocker or "").strip(),
                "step_count": int(step_count or 0),
                "raw_summary": str(raw_summary or "").strip(),
                "content": str(raw_summary or finding or action_taken or "").strip(),
            },
        },
    )


async def save_shell_session_summary(
    *,
    conversation_id: str,
    container_id: str,
    blueprint_id: str,
    container_name: str,
    goal: str,
    findings: str,
    changes_applied: str,
    open_blocker: str,
    step_count: int,
    commands: list[str],
    user_requests: list[str],
    final_stop_reason: str = "",
    summary_parts: dict[str, Any] | None = None,
    raw_summary: str = "",
) -> None:
    conversation = str(conversation_id or "").strip()
    if not conversation or conversation == "global":
        return
    await _hub_call_tool(
        "workspace_event_save",
        {
            "conversation_id": conversation,
            "event_type": "trion_shell_session_summary",
            "event_data": {
                "container_id": str(container_id or "").strip(),
                "blueprint_id": str(blueprint_id or "").strip(),
                "container_name": str(container_name or "").strip(),
                "goal": str(goal or "").strip(),
                "findings": str(findings or "").strip(),
                "changes_applied": str(changes_applied or "").strip(),
                "open_blocker": str(open_blocker or "").strip(),
                "step_count": int(step_count or 0),
                "commands": list(commands or [])[:12],
                "user_requests": list(user_requests or [])[:12],
                "final_stop_reason": str(final_stop_reason or "").strip(),
                "summary_parts": dict(summary_parts or {}),
                "raw_summary": str(raw_summary or "").strip(),
                "content": str(raw_summary or findings or goal or "").strip(),
            },
        },
    )
