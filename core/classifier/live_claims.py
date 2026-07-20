import re
from enum import Enum

# Token-Sets: intelligence_modules/cim_skill_rag/live_claim_tokens.csv
# (PIANO 1.0 Schritt 2.1, 2026-06-11)
from intelligence_modules.cim_skill_rag.live_claim_loader import load_live_claim_tokens


class LiveClaimKind(str, Enum):
    NONE = "none"
    TIME = "time"
    HARDWARE = "hardware"
    FILE_CONTENT = "file_content"
    CONTAINER_RUNTIME = "container_runtime"
    SKILL_INVENTORY = "skill_inventory"


def _tokens(kind: str) -> tuple[str, ...]:
    return load_live_claim_tokens().get(kind, ())


def detect_live_claim_kind(user_text: str) -> LiveClaimKind:
    text = _normalize(user_text)
    if _looks_like_meta_runtime_discussion(text):
        return LiveClaimKind.NONE
    if _contains_any(text, _tokens("file_content")):
        return LiveClaimKind.FILE_CONTENT
    if _contains_any(text, _tokens("hardware")):
        return LiveClaimKind.HARDWARE
    if _contains_any(text, _tokens("container_runtime")):
        return LiveClaimKind.CONTAINER_RUNTIME
    if _contains_any(text, _tokens("skill_inventory")):
        return LiveClaimKind.SKILL_INVENTORY
    if _contains_any(text, _tokens("time")):
        return LiveClaimKind.TIME
    return LiveClaimKind.NONE


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _looks_like_meta_runtime_discussion(text: str) -> bool:
    return _contains_any(text, _tokens("meta_pipeline"))
