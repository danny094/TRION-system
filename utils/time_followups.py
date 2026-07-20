import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


def derive_time_followup_text(user_text: str, facts: dict[str, Any]) -> str:
    offset = parse_time_followup_offset_seconds(user_text)
    base = parse_time_facts(facts)
    if offset is None or base is None:
        return ""
    target = base + timedelta(seconds=offset)
    prefix = describe_offset(user_text, offset)
    return f"{prefix} ist es {target.strftime('%H:%M:%S')} UTC."


def has_derivable_time_followup(user_text: str, orchestrator_context: Mapping[str, Any] | None) -> bool:
    if parse_time_followup_offset_seconds(user_text) is None:
        return False
    if not isinstance(orchestrator_context, Mapping):
        return False
    inner = orchestrator_context.get("context") if "context" in orchestrator_context else orchestrator_context
    grounding_state = inner.get("grounding_state") if isinstance(inner, Mapping) else None
    if not isinstance(grounding_state, Mapping):
        return False
    grounded = grounding_state.get("grounded_results")
    if not isinstance(grounded, list) or len(grounded) != 1:
        return False
    result = grounded[0] if isinstance(grounded[0], Mapping) else {}
    if str(result.get("tool_name") or "").strip() != "time_now":
        return False
    facts = result.get("facts") if isinstance(result.get("facts"), dict) else {}
    return parse_time_facts(facts) is not None


def parse_time_followup_offset_seconds(user_text: str) -> int | None:
    text = _normalize(user_text)
    if "in einer stunde" in text or "in 1 stunde" in text or "in 1 std" in text:
        return 3600
    match = re.search(r"\bin\s+(\d+)\s+stunden?\b", text)
    if match:
        return int(match.group(1)) * 3600
    if "in einer minute" in text or "in 1 minute" in text:
        return 60
    match = re.search(r"\bin\s+(\d+)\s+minuten?\b", text)
    if match:
        return int(match.group(1)) * 60
    return None


def parse_time_facts(facts: dict[str, Any]) -> datetime | None:
    if not isinstance(facts, dict):
        return None
    utc_iso = str(facts.get("utc_iso") or "").strip()
    if utc_iso:
        try:
            return datetime.fromisoformat(utc_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None
    date_value = str(facts.get("date") or "").strip()
    time_value = str(facts.get("time") or "").strip()
    timezone_value = str(facts.get("timezone") or "").strip().upper()
    if date_value and time_value and timezone_value == "UTC":
        try:
            return datetime.fromisoformat(f"{date_value}T{time_value}+00:00").astimezone(timezone.utc)
        except Exception:
            return None
    return None


def describe_offset(user_text: str, offset_seconds: int) -> str:
    text = _normalize(user_text)
    if offset_seconds == 3600 and ("in einer stunde" in text or "in 1 stunde" in text or "in 1 std" in text):
        return "In einer Stunde"
    if offset_seconds % 3600 == 0:
        hours = offset_seconds // 3600
        return f"In {hours} Stunden"
    if offset_seconds == 60 and ("in einer minute" in text or "in 1 minute" in text):
        return "In einer Minute"
    minutes = offset_seconds // 60
    return f"In {minutes} Minuten"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())
