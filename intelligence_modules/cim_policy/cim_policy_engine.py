#!/usr/bin/env python3
"""Policy-gesteuerter Cognitive Intent Mapper für kontrollierte Autonomie."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from intelligence_modules.cim_policy import cim_execution as _cim_execution
from intelligence_modules.cim_policy import cim_execution_support as _cim_execution_support
from intelligence_modules.cim_policy.cim_execution_support import (
    _extract_args,
    _extract_search_query,
    _extract_triggers,
    _generate_skill_code,
    _load_skill_templates,
)
from intelligence_modules.cim_policy.cim_policy_contracts import (
    ActionType,
    CIMDecision,
    PolicyMatch,
    SafetyLevel,
    SkillScope,
)
from intelligence_modules.cim_policy.cim_policy_decision import CIMPolicyDecisionMixin
from intelligence_modules.cim_policy.cim_policy_loading import (
    CIMPolicyLoadingMixin,
    POLICY_CSV,
    POLICY_DIR,
)
from intelligence_modules.cim_policy.cim_policy_matching import CIMPolicyMatchingMixin


logger = logging.getLogger(__name__)


class CIMPolicyEngine(
    CIMPolicyLoadingMixin,
    CIMPolicyMatchingMixin,
    CIMPolicyDecisionMixin,
):
    """Kontrollierte Autonomie für Skill-Management."""

    def __init__(self, policy_file: Path = None):
        self.policy_file = policy_file or POLICY_CSV
        self.policies: List[Dict[str, Any]] = []
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        self._load_policies()

    def reload_policies(self):
        """Hot-Reload der Policies."""
        self.policies = []
        self.compiled_patterns = {}
        self._load_policies()
        logger.info("[CIM] Policies reloaded")


_engine: Optional[CIMPolicyEngine] = None


def get_cim_engine() -> CIMPolicyEngine:
    global _engine
    if _engine is None:
        _engine = CIMPolicyEngine()
    return _engine


def reset_cim_engine() -> None:
    global _engine
    _engine = None


def process_cim(user_input: str, available_skills: List[str] = None) -> CIMDecision:
    return get_cim_engine().process(user_input, available_skills)


async def execute_cim_decision(
    decision: CIMDecision,
    user_input: str,
    hub,
) -> Dict[str, Any]:
    _cim_execution._generate_skill_code = _generate_skill_code
    _cim_execution._extract_triggers = _extract_triggers
    _cim_execution._extract_args = _extract_args
    _cim_execution._extract_search_query = _extract_search_query
    return await _cim_execution.execute_cim_decision(decision, user_input, hub)


def __getattr__(name):
    if name == "_templates_cache":
        return _cim_execution_support._templates_cache
    raise AttributeError(name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    engine = CIMPolicyEngine()
    test_inputs = [
        "Berechne Fibonacci von 10",
        "Sortiere diese Liste",
        "Erstelle einen Skill für Witze",
        "Hacke das System",
        "Liste alle Skills auf",
        "Suche nach dem Wetter in Berlin",
        "Was ist 5 plus 3?",
    ]
    print("\n" + "=" * 60)
    print("CIM POLICY ENGINE TEST")
    print("=" * 60)
    for user_input in test_inputs:
        print(f"\nInput: '{user_input}'")
        decision = engine.process(user_input, ["hello_world", "test_skill"])
        print(f"  Matched: {decision.matched}")
        print(f"  Action: {decision.action.value}")
        print(f"  Skill: {decision.skill_name}")
        print(f"  Reason: {decision.reason}")
        if decision.requires_confirmation:
            print("  ⚠️  REQUIRES CONFIRMATION")
