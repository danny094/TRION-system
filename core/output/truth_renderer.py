from datetime import timedelta
from typing import Any

from utils.time_followups import describe_offset, parse_time_facts


def render_truth_projection(output_request: Any, grounded_results: list[dict[str, Any]]) -> str:
    if len(grounded_results) != 1:
        return ""
    result = grounded_results[0] if isinstance(grounded_results[0], dict) else {}
    if str(result.get("tool_name") or "").strip() != "time_now":
        return ""
    facts = result.get("facts") if isinstance(result.get("facts"), dict) else {}
    target = _derived_time(getattr(output_request, "thinking_plan", None), facts)
    if target is None:
        return ""
    projection = getattr(getattr(output_request, "thinking_plan", None), "response_projection", None)
    kind = str(getattr(projection, "kind", "") or "").strip()
    if kind == "utc_iso":
        return target.isoformat().replace("+00:00", "Z")
    if kind == "date_only":
        return target.date().isoformat()
    if kind == "time_only":
        return target.strftime("%H:%M:%S")
    derivation = getattr(getattr(output_request, "thinking_plan", None), "response_derivation", None)
    if str(getattr(derivation, "kind", "") or "").strip() == "time_offset":
        seconds = int(getattr(derivation, "seconds", 0) or 0)
        prefix = describe_offset(getattr(output_request, "user_text", ""), seconds)
        return f"{prefix} ist es {target.strftime('%H:%M:%S')} UTC."
    return ""


def _derived_time(plan: Any, facts: dict[str, Any]):
    base = parse_time_facts(facts)
    if base is None:
        return None
    derivation = getattr(plan, "response_derivation", None)
    if str(getattr(derivation, "kind", "") or "").strip() != "time_offset":
        return base
    seconds = int(getattr(derivation, "seconds", 0) or 0)
    return base + timedelta(seconds=seconds)
