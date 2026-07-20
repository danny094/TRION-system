from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


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


@dataclass(frozen=True)
class EvidenceBundle:
    grounded_tool_results: List[Dict[str, Any]] = field(default_factory=list)
    relevant_carryover_results: List[Dict[str, Any]] = field(default_factory=list)
    task_loop_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    available_tool_details: List[Dict[str, Any]] = field(default_factory=list)
    selected_tool_details: List[Dict[str, Any]] = field(default_factory=list)
    home_context: Dict[str, Any] = field(default_factory=dict)
    self_context: Dict[str, Any] = field(default_factory=dict)
