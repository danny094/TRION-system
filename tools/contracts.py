from dataclasses import dataclass, field
from typing import Any, Dict, Optional


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
    success: bool
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_s: float = 0.0
