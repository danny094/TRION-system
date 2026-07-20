from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    SAFE = "safe"
    NEEDS_CONFIRMATION = "needs_confirmation"
    BLOCK = "block"


class PlanContractViolation(ValueError):
    pass


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    title: str
    goal: str
    tool: Optional[str] = None
    tool_arguments: Dict[str, Any] = field(default_factory=dict)
    timeout_s: Optional[float] = None
    risk: RiskLevel = RiskLevel.SAFE
    done_when: str = ""
    required_evidence: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResponseProjection:
    kind: str


@dataclass(frozen=True)
class ResponseDerivation:
    kind: str
    seconds: int = 0


@dataclass(frozen=True)
class AdditionalEvidenceNeed:
    kind: str
    reason: str = ""
    candidate_tools: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ThinkingPlan:
    intent: str
    steps: List[PlanStep]
    needs_task_loop: bool
    risk_level: RiskLevel
    reasoning: str = ""
    suggested_tools: List[str] = field(default_factory=list)
    context_hints: Dict[str, Any] = field(default_factory=dict)
    plan_id: str = ""
    response_projection: Optional[ResponseProjection] = None
    response_derivation: Optional[ResponseDerivation] = None
    additional_evidence_need: Optional[AdditionalEvidenceNeed] = None

    @classmethod
    def from_dict(cls, value: Any) -> Optional["ThinkingPlan"]:
        """Parse persisted plan data through the canonical schema owner."""
        from core.thinking.plan_schema import parse_thinking_plan

        return parse_thinking_plan(value)
