from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class CapabilityState:
    name: str
    description: str = ""
    status: str = "unknown"
    source: str = ""
    confidence: float = 0.0
    checked_at: str | None = None
    scope: str = "agent"


@dataclass(frozen=True)
class SelfContext:
    identity: Dict[str, Any]
    current_scope: Dict[str, Any]
    capabilities: List[CapabilityState] = field(default_factory=list)
    memory_visibility: Dict[str, Any] = field(default_factory=dict)
    uncertainties: List[Dict[str, Any]] = field(default_factory=list)
