import hashlib
import logging
import re
from typing import Dict, Optional, Tuple


logger = logging.getLogger("intelligence_modules.cim_policy.cim_policy_engine")


class CIMPolicyMatchingMixin:
    def _match_intent(self, user_input: str) -> Optional[Tuple[Dict, float]]:
        """Matched User-Input gegen alle Policies."""
        user_lower = user_input.lower().strip()
        for policy in self.policies:
            pattern_id = policy["pattern_id"]
            pattern = self.compiled_patterns.get(pattern_id)
            if not pattern:
                continue
            match = pattern.search(user_lower)
            if not match:
                continue
            match_len = len(match.group())
            input_len = len(user_lower)
            match_confidence = min(1.0, match_len / max(input_len * 0.3, 1))
            min_confidence = policy["intent_confidence"]
            if policy.get("requires_confirmation", False):
                effective_confidence = max(match_confidence, min_confidence)
                logger.debug(
                    f"[CIM] Matched (confirm-gated): {pattern_id} "
                    f"(conf={effective_confidence:.2f})"
                )
                return policy, effective_confidence
            if match_confidence >= min_confidence * 0.8:
                logger.debug(
                    f"[CIM] Matched: {pattern_id} (conf={match_confidence:.2f})"
                )
                return policy, match_confidence
        return None

    def _derive_skill_name(self, user_input: str, policy: Dict) -> str:
        """Leitet deterministischen Skill-Namen aus Intent ab."""
        explicit_name = self._extract_explicit_skill_name(user_input)
        if explicit_name:
            return explicit_name
        category = policy.get("trigger_category", "general")
        keywords = []
        user_lower = user_input.lower()
        math_keywords = [
            "fibonacci", "fakultät", "factorial", "primzahl", "wurzel",
            "quadrat", "addition", "subtraktion", "multiplikation", "division",
        ]
        data_keywords = [
            "csv", "json", "sortier", "filter", "tabelle", "liste", "konvertier",
        ]
        for keyword in math_keywords + data_keywords:
            if keyword in user_lower:
                keywords.append(
                    keyword.replace("ä", "ae").replace("ü", "ue").replace("ö", "oe")
                )
        if keywords:
            skill_name = f"auto_{category}_{keywords[0]}"
        else:
            hash_suffix = hashlib.md5(user_input.encode()).hexdigest()[:6]
            skill_name = f"auto_{category}_{hash_suffix}"
        skill_name = re.sub(r"[^a-z0-9_]", "_", skill_name.lower())
        return re.sub(r"_+", "_", skill_name).strip("_")

    def _extract_explicit_skill_name(self, user_input: str) -> Optional[str]:
        """Try user-provided names before falling back to auto naming."""
        text = (user_input or "").strip()
        if not text:
            return None
        patterns = [
            r"(?:skill|funktion)\s+namens\s+[`\"']?([A-Za-z][A-Za-z0-9_-]{2,63})[`\"']?",
            r"(?:namens|named|called|name)\s+[`\"']?([A-Za-z][A-Za-z0-9_-]{2,63})[`\"']?",
        ]
        stopwords = {
            "skill", "funktion", "function", "neu", "neue", "new",
            "bitte", "einen", "eine", "einer", "den", "die", "das",
        }
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE)
            if not match:
                continue
            candidate = match.group(1).strip("`\"'.,:;!?()[]{} ").lower()
            candidate = re.sub(r"[^a-z0-9_]", "_", candidate.replace("-", "_"))
            candidate = re.sub(r"_+", "_", candidate).strip("_")
            if len(candidate) >= 3 and candidate not in stopwords:
                return candidate
        return None
