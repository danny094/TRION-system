from dataclasses import dataclass
from enum import Enum


class Category(str, Enum):
    SMALLTALK = "smalltalk"
    RISK = "risk"
    TOOL = "tool"
    PLANNING = "planning"
    INFORMATION = "information"
    UNKNOWN = "unknown"


class SafetyLevel(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    BLOCK = "block"


class Route(str, Enum):
    DIRECT_TO_THINKING = "direct_to_thinking"
    NEEDS_ORCHESTRATOR = "needs_orchestrator"
    BLOCK = "block"


@dataclass(frozen=True)
class ClassifierResult:
    category: Category
    safety_level: SafetyLevel
    needs_orchestrator: bool
    confidence: float
    route: Route
    matched_pattern: str = ""
    reason: str = ""
    is_long_document: bool = False
    estimated_input_tokens: int = 0
