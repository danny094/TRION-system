import ast
from typing import Optional

from core.verifier.input_prepare import VerifierInput


def normalize_warnings(warnings: list[str], verifier_input: VerifierInput) -> list[str]:
    focus = str(verifier_input.document_meta.get("question_focus") or "").strip().lower()
    if focus not in {"semantic", "structure", "exact"}:
        return warnings
    result: list[str] = []
    for warning in warnings:
        if _drop_for_focus(warning, focus):
            continue
        result.append(_rewrite_for_focus(warning, focus))
    return result


def _drop_for_focus(warning: str, focus: str) -> bool:
    lowered = warning.lower()
    if focus == "structure" and "priorisiert semantische inhaltsfragen" in lowered:
        return True
    if focus == "semantic" and any(
        token in lowered for token in (
            "falls der user nach struktur statt inhalt fragt",
            "kapitelanzahl relevant wäre",
            "kapitelanzahl relevant waere",
        )
    ):
        return True
    return False


def _rewrite_for_focus(warning: str, focus: str) -> str:
    parsed = _parse_warning_object(warning)
    if not parsed:
        return warning
    message = str(parsed.get("message") or "").strip()
    suggestion = str(parsed.get("suggestion") or "").strip()
    if focus == "structure":
        message = message.replace("semantische Inhaltsfragen", "Strukturfragen")
        message = message.replace("semantische Interpretation", "Strukturauswertung")
    if focus == "semantic":
        message = message.replace("Strukturabdeckung sicherstellt", "Navigation unterstuetzt")
        message = message.replace("strukturbezogenen", "navigationsbezogenen")
    return str({"type": parsed.get("type"), "message": message, "suggestion": suggestion})


def _parse_warning_object(warning: str) -> Optional[dict]:
    try:
        value = ast.literal_eval(warning)
        return value if isinstance(value, dict) else None
    except Exception:
        return None
