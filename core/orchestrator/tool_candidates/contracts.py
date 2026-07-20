from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCandidate:
    tool_name: str
    score: float
    semantic_score: float
    semantic_available: bool
    lexical_score: int
    gate: str
