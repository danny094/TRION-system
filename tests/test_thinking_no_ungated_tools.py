"""P11 SP3-H: Thinking darf keine ungegateten Tools zurückholen.

Wenn der Orchestrator selected_tool_details == [] liefert (Eligibility-Gate
hat nichts freigegeben), darf Thinking weder im Fallback- noch im LLM-Pfad
Tools aus available_tool_details vorschlagen. available_tool_details ist
hoechstens Kontext/Anzeige, nicht Vorschlagsquelle (Danny-Vorgabe, SP3-H).

Bezug: SP3-G-Inventarbericht — Schatten-Autoritaet zwischen Orchestrator-
Eligibility-Gate und Thinkings eigenem Keyword-/LLM-Fallback auf
available_tools.
"""
from __future__ import annotations

from typing import Any, Dict

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.thinking.analyzer import analyze_request
from core.thinking.fallback.tools import suggested_tools


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        route=Route.DIRECT_TO_THINKING,
        needs_orchestrator=False,
        confidence=0.9,
        matched_pattern="",
    )


def _frame_none() -> Dict[str, Any]:
    """routing_frame, der zeigt: Pipeline ist gelaufen, live_claim NONE."""
    return {
        "intent_kind": "action_request",
        "execution_mode": "single_tool",
        "evidence_need": "none",
        "source_signals": {
            "live_claim": "none",
            "dialogue_signal": {
                "dialogue_act": "request",
                "response_tone": "neutral",
                "response_length_hint": "medium",
                "confidence": 0.7,
                "classifier_mode": "lexical",
            },
        },
    }


class TestFallbackPathNoUngatedTools:
    """Szenario 1 (Danny SP3-H): Fallback-Pfad, selected leer, live_claim NONE."""

    def test_empty_selected_with_routing_frame_yields_no_suggestion(self):
        result = suggested_tools(
            "speichere diesen fakt.",
            ["memory_save"],
            [],
            _classifier(),
            None,
            {"routing_frame": _frame_none()},
            None,
        )
        assert result == []


class TestLlmPathNoUngatedTools:
    """Szenario 2 (Danny SP3-H): LLM-Pfad, selected leer, LLM schlaegt trotzdem
    ein Tool vor → Vorschlag wird verworfen/auf [] normalisiert."""

    def test_llm_suggestion_discarded_when_selected_tools_empty(self):
        async def fake_complete_prompt(**kwargs):
            return (
                '{"intent":"answer_user","suggested_tools":["memory_save"],'
                '"reasoning":"hallucinated tool choice."}'
            )

        raw = analyze_request(
            "speichere diesen fakt.",
            _classifier(),
            available_tools=[{"name": "memory_save"}],
            selected_tools=[],
            orchestrator_context={"routing_frame": _frame_none()},
            complete_prompt_fn=fake_complete_prompt,
            llm_enabled=True,
        )

        assert raw["suggested_tools"] == []


class TestPositiveCaseEligibleToolVisible:
    """Szenario 3 (Danny SP3-H): selected_tools enthaelt ein eligible Tool —
    Thinking darf genau dieses Tool sehen/vorschlagen (Fallback- und LLM-Pfad)."""

    def test_fallback_path_returns_exact_selected_tool(self):
        result = suggested_tools(
            "speichere diesen fakt.",
            ["memory_save", "memory_search"],
            ["memory_save"],
            _classifier(),
            None,
            {"routing_frame": _frame_none()},
            None,
        )
        assert result == ["memory_save"]

    def test_llm_path_keeps_exact_selected_tool_when_llm_omits_suggestion(self):
        async def fake_complete_prompt(**kwargs):
            return '{"intent":"answer_user","reasoning":"Need to save a fact."}'

        raw = analyze_request(
            "speichere diesen fakt.",
            _classifier(),
            available_tools=[{"name": "memory_save"}, {"name": "memory_search"}],
            selected_tools=["memory_save"],
            complete_prompt_fn=fake_complete_prompt,
            llm_enabled=True,
        )

        assert raw["suggested_tools"] == ["memory_save"]
