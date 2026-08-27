from dataclasses import dataclass, field
from typing import Any, Dict

from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff


@dataclass(frozen=True)
class OutputRequest:
    user_text: str
    thinking_plan: Any
    output_evidence: OutputEvidenceHandoff
    renderable_evidence: tuple["RenderableEvidence", ...] = ()
    context: Dict[str, Any] = field(default_factory=dict)
    stream: bool = True

    def __post_init__(self) -> None:
        evidence = tuple(self.renderable_evidence)
        if any(type(item) is not RenderableEvidence for item in evidence):
            raise TypeError("renderable_evidence must contain RenderableEvidence values")
        object.__setattr__(self, "renderable_evidence", evidence)


@dataclass(frozen=True)
class OutputResult:
    content: str
    truncated: bool = False
    postcheck_applied: bool = False


@dataclass(frozen=True)
class RenderableEvidence:
    summary: str
    bullets: tuple[str, ...] = ()
