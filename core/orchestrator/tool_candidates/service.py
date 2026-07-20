from typing import List

from config.models import (
    get_tool_selector_ambiguity_margin,
    get_tool_selector_high_similarity,
    get_tool_selector_lexical_only_keyword_hits_min,
    get_tool_selector_lexical_only_min,
    get_tool_selector_lexical_support_min,
    get_tool_selector_min_similarity,
    get_tool_selector_strong_lexical_boost,
    get_tool_selector_weak_lexical_boost,
)
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_candidates.contracts import ToolCandidate
from core.orchestrator.tool_candidates.embedding import semantic_score
from core.orchestrator.tool_candidates.scoring import score_tool_breakdown


def select_top_k_tools(
    user_text: str,
    available_tools: List[ToolDescriptor],
    *,
    top_k: int = 3,
) -> List[ToolDescriptor]:
    ranked = rank_tool_candidates(user_text, available_tools)
    winners = ranked[: max(1, int(top_k))]
    by_name = {tool.name: tool for tool in available_tools}
    return [by_name[candidate.tool_name] for candidate in winners if candidate.tool_name in by_name]


def rank_tool_candidates(user_text: str, available_tools: List[ToolDescriptor]) -> List[ToolCandidate]:
    ranked = [
        _score_candidate(user_text, tool)
        for tool in available_tools
    ]
    ranked = [candidate for candidate in ranked if candidate is not None]
    ranked.sort(key=lambda candidate: (-candidate.score, candidate.tool_name))
    return _apply_margin_gate(ranked)


def _score_candidate(user_text: str, tool: ToolDescriptor) -> ToolCandidate | None:
    breakdown = score_tool_breakdown(user_text, tool)
    semantic_raw = semantic_score(user_text, tool)
    semantic_available = semantic_raw is not None
    semantic = float(semantic_raw or 0.0)
    gate = _gate_candidate(semantic, semantic_available=semantic_available, breakdown=breakdown)
    if gate is None:
        return None
    return ToolCandidate(
        tool_name=tool.name,
        score=_combined_score(semantic, breakdown.total, gate=gate),
        semantic_score=semantic,
        semantic_available=semantic_available,
        lexical_score=breakdown.total,
        gate=gate,
    )


def _gate_candidate(semantic: float, *, semantic_available: bool, breakdown) -> str | None:
    if not semantic_available:
        if (
            breakdown.total >= get_tool_selector_lexical_only_min()
            and (breakdown.keyword_hits + breakdown.example_hits) >= get_tool_selector_lexical_only_keyword_hits_min()
        ):
            return "lexical_only"
        return None
    if semantic < get_tool_selector_min_similarity():
        return None
    if semantic >= get_tool_selector_high_similarity():
        return "strong"
    if breakdown.total >= get_tool_selector_lexical_support_min():
        return "weak_with_lexical_support"
    return None


def _combined_score(semantic: float, lexical: int, *, gate: str) -> float:
    lexical_normalized = min(max(lexical, 0), 10) / 10.0
    if gate == "strong":
        return semantic * (1.0 + get_tool_selector_strong_lexical_boost() * lexical_normalized)
    if gate == "weak_with_lexical_support":
        return semantic * (1.0 + get_tool_selector_weak_lexical_boost() * lexical_normalized)
    return min(max(lexical, 0), 50) / 50.0


def _apply_margin_gate(ranked: List[ToolCandidate]) -> List[ToolCandidate]:
    if len(ranked) < 2:
        return ranked
    top = ranked[0]
    second = ranked[1]
    margin = top.score - second.score
    if top.gate != "strong" and margin < get_tool_selector_ambiguity_margin():
        return []
    return ranked
