import re

from core.output.contracts import OutputRequest
from core.output.grounded_output_selection import _normalize_text
from core.pipeline.output_evidence_contracts import OutputEvidenceState


_POSITIVE_EXECUTION_SUBJECTS = ("ich habe", "wir haben")
_POSITIVE_EXECUTION_ACTIONS = (
    "getestet", "geprueft", "geprüft", "probiert", "versucht", "ausgefuehrt", "ausgeführt", "gesucht",
)
_POSITIVE_EXECUTION_ACTION_PATTERN = "|".join(map(re.escape, _POSITIVE_EXECUTION_ACTIONS))
_POSITIVE_EXECUTION_PATTERNS = tuple(
    rf"\b{re.escape(subject)}\b.*\b({_POSITIVE_EXECUTION_ACTION_PATTERN})\b"
    for subject in _POSITIVE_EXECUTION_SUBJECTS
)
_POSITIVE_EXECUTION_SUBJECT_PATTERN = "|".join(
    re.escape(subject).replace(r"\ ", r"\s+") for subject in _POSITIVE_EXECUTION_SUBJECTS
)
_NEGATED_EXECUTION_PATTERNS = (
    r"\bkonnte\b.*\b(nicht|keine)\b",
    r"\bkonnte ich\b.*\bnicht\b",
    r"\bnicht ausgefuehrt\b",
    r"\bnicht ausgeführt\b",
    r"\bkein passendes tool\b",
    r"\bkeine suchfunktion\b",
    r"\bnicht verifizieren\b",
)


def apply_execution_consistency_guard(output_request: OutputRequest, content: str) -> str:
    if not str(content or "").strip():
        return content
    if not _claims_positive_execution(content):
        return content
    if _contains_negated_execution(content):
        return content
    if _has_positive_execution_evidence(output_request):
        return content
    return (
        "Ich kann diese Ausfuehrung gerade nicht als erfolgt bestaetigen. "
        "Es liegen keine positiven Ausfuehrungsbelege fuer einen gestarteten und erfolgreich gelaufenen Schritt vor."
    )


def execution_claim_pending_start(output_request: OutputRequest, content: str) -> int | None:
    if _has_positive_execution_evidence(output_request):
        return None
    lowered = str(content or "").casefold()
    match = re.search(rf"(?<!\w)(?:{_POSITIVE_EXECUTION_SUBJECT_PATTERN})\b", lowered)
    if match is not None:
        return match.start()
    suffix_floor = max(0, len(lowered) - max(map(len, _POSITIVE_EXECUTION_SUBJECTS)) + 1)
    for start in range(suffix_floor, len(lowered)):
        if start > 0 and lowered[start - 1].isalnum():
            continue
        suffix = re.sub(r"\s+", " ", lowered[start:])
        if suffix and any(subject.startswith(suffix) for subject in _POSITIVE_EXECUTION_SUBJECTS):
            return start
    return None


def _claims_positive_execution(content: str) -> bool:
    text = _normalize_text(content)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _POSITIVE_EXECUTION_PATTERNS)


def _contains_negated_execution(content: str) -> bool:
    text = _normalize_text(content)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _NEGATED_EXECUTION_PATTERNS)


def _has_positive_execution_evidence(output_request: OutputRequest) -> bool:
    return output_request.output_evidence.state is OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE
