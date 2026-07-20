"""Output-side helpers for capability-question evidence decisions."""
from __future__ import annotations

import re


def is_active_container_capability_question(user_text: str) -> bool:
    text = _normalize(user_text)
    if not _mentions_any(text, ("container", "home", "zuhause", "trion-home", "hier")):
        return False
    capability_tokens = (
        "was kannst du",
        "was kann ich",
        "was koenntest du",
        "was könntest du",
        "was ist moeglich",
        "was ist möglich",
        "welche capabilities",
        "welche faehigkeiten",
        "welche fähigkeiten",
        "welche moeglichkeiten",
        "welche möglichkeiten",
    )
    return _mentions_any(text, capability_tokens)


def _mentions_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())
