import csv
import logging
import re
from typing import Any, Dict, List, Optional

from intelligence_modules.cim_policy.cim_policy_loading import POLICY_DIR


logger = logging.getLogger("intelligence_modules.cim_policy.cim_policy_engine")
_templates_cache: Optional[List[Dict]] = None


def _load_skill_templates() -> List[Dict]:
    """Load skill templates from CSV (cached)."""
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    csv_path = POLICY_DIR / "skill_templates.csv"
    if not csv_path.exists():
        logger.warning(f"skill_templates.csv not found at {csv_path}")
        return []
    templates = []
    with open(csv_path, "r", encoding="utf-8") as template_stream:
        reader = csv.DictReader(template_stream)
        for row in reader:
            keywords_raw = row.get("intent_keywords", "")
            row["_keywords"] = [
                keyword.strip().lower()
                for keyword in keywords_raw.split("|")
                if keyword.strip()
            ]
            templates.append(row)
    _templates_cache = templates
    return templates


async def _generate_skill_code(user_input: str, skill_name: str, hub) -> str:
    """Generiert Python-Code anhand passender Skill-Templates."""
    user_lower = user_input.lower()
    templates = _load_skill_templates()
    best_match = None
    best_score = 0
    for template in templates:
        score = sum(1 for keyword in template["_keywords"] if keyword in user_lower)
        if score > best_score:
            best_score = score
            best_match = template
    if best_match and best_score > 0:
        code = best_match.get("code_template", "")
        logger.info(
            f"[CIMPolicy] Template matched: {best_match.get('template_id')} "
            f"(score={best_score})"
        )
        return code
    return f'''\ndef run(input_text: str = "") -> dict:\n    """Auto-generierter Skill für: {user_input[:30]}"""\n    return {{"input": input_text, "processed": True}}\n'''


def _extract_triggers(user_input: str) -> List[str]:
    words = user_input.lower().split()
    keywords = [
        "berechne", "kalkuliere", "fibonacci", "fakultät", "wurzel",
        "sortiere", "filtere", "konvertiere", "liste",
    ]
    triggers = [keyword for word in words for keyword in keywords if keyword in word]
    return list(set(triggers)) if triggers else ["auto"]


def _extract_args(user_input: str) -> Dict[str, Any]:
    args = {}
    numbers = re.findall(r"\d+\.?\d*", user_input)
    if numbers:
        args["n"] = int(float(numbers[0]))
    return args


def _extract_search_query(user_input: str) -> str:
    query = re.sub(
        r"(suche nach|suche im internet|google mal|recherchiere)",
        "",
        user_input,
        flags=re.IGNORECASE,
    )
    return query.strip()
