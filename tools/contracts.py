from dataclasses import dataclass, field
from typing import Any, Dict

from mcp.tool_result_contracts import MCPToolResultEnvelope


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    step_id: str = ""
    timeout_s: float = 30.0


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    step_id: str
    envelope: MCPToolResultEnvelope
    duration_s: float = 0.0
