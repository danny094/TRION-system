import logging
from typing import List

from intelligence_modules.cim_policy.cim_policy_contracts import (
    ActionType,
    CIMDecision,
    PolicyMatch,
    SafetyLevel,
    SkillScope,
)


logger = logging.getLogger("intelligence_modules.cim_policy.cim_policy_engine")


class CIMPolicyDecisionMixin:
    def process(self, user_input: str, available_skills: List[str] = None) -> CIMDecision:
        """Verarbeitet User-Input und trifft die Policy-Entscheidung."""
        available_skills = available_skills or []
        match_result = self._match_intent(user_input)
        if not match_result:
            return CIMDecision(
                matched=False,
                action=ActionType.FALLBACK_CHAT,
                reason="Kein Policy-Pattern matched",
            )

        policy, confidence = match_result
        pattern_id = policy["pattern_id"]
        skill_name = self._derive_skill_name(user_input, policy)
        safety_level = SafetyLevel(policy.get("safety_level", "low"))
        skill_scope = SkillScope(policy.get("skill_scope", "stateless"))

        if safety_level == SafetyLevel.CRITICAL:
            action_if_missing = policy.get("action_if_missing", "")
            if action_if_missing == "force_create_skill":
                logger.warning("[CIM] BLOCKED: Auto-create denied for critical safety level")
                return CIMDecision(
                    matched=True,
                    action=ActionType.DENY_AUTONOMY,
                    skill_name=skill_name,
                    requires_confirmation=True,
                    reason="Sicherheitslevel CRITICAL - Autonome Erstellung verboten",
                )

        if skill_scope == SkillScope.SYSTEM:
            if policy.get("action_if_missing") == "force_create_skill":
                logger.warning("[CIM] BLOCKED: Cannot auto-create system scope skill")
                return CIMDecision(
                    matched=True,
                    action=ActionType.DENY_AUTONOMY,
                    skill_name=skill_name,
                    reason="System-Scope Skills können nicht automatisch erstellt werden",
                )

        check_exists = policy.get("check_skill_exists", False)
        skill_exists = any(
            item.lower() == skill_name.lower() or skill_name in item.lower()
            for item in available_skills
        )
        if check_exists:
            action_string = policy.get(
                "action_if_present" if skill_exists else "action_if_missing",
                "run_skill" if skill_exists else "fallback_chat",
            )
        else:
            action_string = policy.get("action_if_present", "fallback_chat")
        try:
            action = ActionType(action_string)
        except ValueError:
            logger.warning(f"[CIM] Unknown action: {action_string}")
            action = ActionType.FALLBACK_CHAT

        fallback_string = policy.get("fallback_action", "fallback_chat")
        try:
            fallback_action = ActionType(fallback_string)
        except ValueError:
            fallback_action = ActionType.FALLBACK_CHAT

        policy_match = PolicyMatch(
            pattern_id=pattern_id,
            trigger_category=policy.get("trigger_category", ""),
            confidence=confidence,
            action=action,
            skill_scope=skill_scope,
            safety_level=safety_level,
            requires_confirmation=policy.get("requires_confirmation", False),
            allows_chaining=policy.get("allows_chaining", False),
            derived_skill_name=skill_name,
            fallback_action=fallback_action,
        )
        decision = CIMDecision(
            matched=True,
            action=action,
            skill_name=skill_name,
            requires_confirmation=policy.get("requires_confirmation", False),
            policy_match=policy_match,
            reason=f"Pattern '{pattern_id}' matched mit Confidence {confidence:.2f}",
        )
        logger.info(
            f"[CIM] Decision: {action.value} for skill '{skill_name}' ({pattern_id})"
        )
        return decision
