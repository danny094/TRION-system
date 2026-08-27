from dataclasses import dataclass
from enum import Enum


class ClaimType(str, Enum):
    RUNTIME_TIME = "runtime_time"
    RUNTIME_HARDWARE = "runtime_hardware"
    FILE_CONTENT = "file_content"
    CONTAINER_RUNTIME = "container_runtime"
    SKILL_INVENTORY = "skill_inventory"
    CONCEPTUAL_ANALYSIS = "conceptual_analysis"


class GuardDecision(str, Enum):
    ALLOW = "allow"
    LIMIT_TO_VERIFIED = "limit_to_verified"
    EXPLICIT_UNKNOWN = "explicit_unknown"
    ASK_FOR_CLARIFICATION = "ask_for_clarification"


@dataclass(frozen=True)
class EvidenceClaim:
    claim_type: ClaimType
    user_text: str
    required_truth_source: str
