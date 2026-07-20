from __future__ import annotations

import re

# Token-Sets: intelligence_modules/cim_skill_rag/dialogue_signal_tokens.csv
# (PIANO 1.0 Schritt 2.2, 2026-06-11)
from intelligence_modules.cim_skill_rag.dialogue_signal_loader import load_dialogue_signal_tokens

from core.dialogue_signal.contracts import DialogueSignal


def _tokens(act: str) -> tuple[str, ...]:
    return load_dialogue_signal_tokens().get(act, ())


def classify_dialogue_signal(user_text: str) -> DialogueSignal:
    text = str(user_text or "").strip()
    lower = _normalize(text)
    tokens = _tokenize(lower)
    token_set = set(tokens)
    is_question = "?" in text or bool(tokens and tokens[0] in _tokens("question_word"))

    if _contains_any(lower, _tokens("feedback")):
        return DialogueSignal("feedback", "mirror_user", "short", 0.9)
    if _contains_any(lower, _tokens("smalltalk")):
        return DialogueSignal("smalltalk", "warm", "short", 0.82)
    if _contains_any(lower, _tokens("analysis")):
        return DialogueSignal("analysis", "neutral", "medium", 0.8)
    if _contains_any(lower, _tokens("request")):
        return DialogueSignal("request", "mirror_user", "short", 0.78)
    if is_question:
        return DialogueSignal("question", "mirror_user", "short", 0.72)
    if token_set.intersection(_tokens("ack")):
        return DialogueSignal("ack", "mirror_user", "short", 0.7)
    return DialogueSignal("request", "neutral", "medium", 0.55)


def is_conversational_dialogue_act(signal: DialogueSignal | None) -> bool:
    if signal is None:
        return False
    return signal.dialogue_act in {"smalltalk", "feedback", "ack"}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-zA-ZäöüÄÖÜß]+", value)


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)

