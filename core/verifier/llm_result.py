from typing import Optional

from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import VerifierInput
from core.verifier.llm_warnings import normalize_warnings


def result_from_payload(
    payload: dict,
    verifier_input: VerifierInput,
) -> Optional[VerifierResult]:
    if not _has_explicit_decision(payload):
        return _invalid("control_llm_invalid_decision",
                        "Die Verifier-Entscheidung war unvollstaendig. Liefere ein eindeutiges approved/hard_block-Verdict im JSON.")
    hard_block = bool(payload.get("hard_block"))
    approved = bool(payload.get("approved"))
    if hard_block and approved:
        return _invalid("control_llm_conflicting_decision",
                        "Die Verifier-Entscheidung war widerspruechlich. Liefere genau ein eindeutiges Verdict.")
    reason = str(payload.get("final_instruction") or payload.get("block_reason_code") or "").strip()
    warnings = [str(w) for w in list(payload.get("warnings") or []) if str(w).strip()]
    warnings = normalize_warnings(warnings, verifier_input)
    hint = _hint_from_payload(payload)
    if hard_block:
        return VerifierResult(verdict=Verdict.HARD_BLOCK,
                              reason=reason or "Control layer hard blocked the plan.", warnings=warnings)
    if approved:
        return VerifierResult(verdict=Verdict.APPROVED,
                              reason=reason or "Control layer approved the plan.", warnings=warnings)
    return VerifierResult(verdict=Verdict.REJECTED, hint=hint,
                          reason=reason or "Control layer rejected the plan.", warnings=warnings)


def _has_explicit_decision(payload: dict) -> bool:
    return "approved" in payload or "hard_block" in payload


def _hint_from_payload(payload: dict) -> Optional[str]:
    corrections = payload.get("corrections")
    if isinstance(corrections, dict):
        for key in ("final_instruction", "resolution_strategy", "hallucination_risk"):
            value = corrections.get(key)
            if str(value or "").strip():
                return str(value).strip()
    final_instruction = str(payload.get("final_instruction") or "").strip()
    return final_instruction or None


def _invalid(reason: str, hint: str) -> VerifierResult:
    return VerifierResult(verdict=Verdict.REJECTED, hint=hint, reason=reason, warnings=[reason])
