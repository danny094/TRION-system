from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Verdict(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    HARD_BLOCK = "hard_block"


@dataclass(frozen=True)
class VerifierResult:
    verdict: Verdict
    hint: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    reason: str = ""
