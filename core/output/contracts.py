from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class OutputRequest:
    user_text: str
    thinking_plan: Any
    context: Dict[str, Any] = field(default_factory=dict)
    stream: bool = True


@dataclass(frozen=True)
class OutputResult:
    content: str
    truncated: bool = False
    postcheck_applied: bool = False


@dataclass(frozen=True)
class RenderableEvidence:
    tool_name: str
    summary: str
    bullets: List[str] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)
