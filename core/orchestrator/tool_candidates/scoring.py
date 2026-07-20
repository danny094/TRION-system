import re
from dataclasses import dataclass
from typing import Iterable

from core.orchestrator.contracts import ToolDescriptor


@dataclass(frozen=True)
class LexicalScoreBreakdown:
    total: int
    keyword_hits: int
    example_hits: int
    intent_description_hits: int
    description_hits: int


def score_tool(user_text: str, tool: ToolDescriptor) -> int:
    return score_tool_breakdown(user_text, tool).total


def score_tool_breakdown(user_text: str, tool: ToolDescriptor) -> LexicalScoreBreakdown:
    text = _normalize(user_text)
    if not text:
        return LexicalScoreBreakdown(0, 0, 0, 0, 0)
    keyword_hits = _field_hits(text, tool.intent_keywords)
    example_hits = _field_hits(text, tool.intent_examples)
    intent_description_hits = _field_hits(text, [tool.intent_description])
    description_hits = _field_hits(text, [tool.description])
    total = (
        keyword_hits * 6
        + example_hits * 4
        + intent_description_hits * 2
        + description_hits
    )
    return LexicalScoreBreakdown(
        total=total,
        keyword_hits=keyword_hits,
        example_hits=example_hits,
        intent_description_hits=intent_description_hits,
        description_hits=description_hits,
    )


def _field_hits(text: str, values: Iterable[str]) -> int:
    hits = 0
    for value in values:
        normalized = _normalize(value)
        if _matches(text, normalized):
            hits += 1
    return hits


def _normalize(value: str) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _matches(text: str, normalized: str) -> bool:
    if not normalized:
        return False
    if " " in normalized:
        return _token_overlap(text, normalized) >= 2
    return re.search(rf"\b{re.escape(normalized)}\b", text) is not None


def _token_overlap(left: str, right: str) -> int:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    return len(left_tokens & right_tokens)


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"\w+", value.lower()) if len(token) >= 3]
