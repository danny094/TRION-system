from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SafetyLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SkillScope(Enum):
    STATELESS = "stateless"
    SESSION = "session"
    PERSISTENT = "persistent"
    SYSTEM = "system"


class ActionType(Enum):
    FORCE_CREATE_SKILL = "force_create_skill"
    FORCE_RUN_SKILL = "force_run_skill"
    RUN_SKILL = "run_skill"
    LIST_SKILLS = "list_skills"
    WEB_SEARCH = "web_search"
    POLICY_CHECK = "policy_check"
    DENY_AUTONOMY = "deny_autonomy"
    REQUEST_USER_CONFIRMATION = "request_user_confirmation"
    FALLBACK_CHAT = "fallback_chat"
    RETRY_ONCE = "retry_once"
    MARK_SKILL_UNSTABLE = "mark_skill_unstable"


@dataclass
class PolicyMatch:
    """Ergebnis eines Policy-Matches."""
    pattern_id: str
    trigger_category: str
    confidence: float
    action: ActionType
    skill_scope: SkillScope
    safety_level: SafetyLevel
    requires_confirmation: bool
    allows_chaining: bool
    derived_skill_name: Optional[str] = None
    fallback_action: Optional[ActionType] = None


@dataclass
class CIMDecision:
    """Finale CIM-Entscheidung."""
    matched: bool
    action: ActionType
    skill_name: Optional[str] = None
    requires_confirmation: bool = False
    policy_match: Optional[PolicyMatch] = None
    reason: str = ""
