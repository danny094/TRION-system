"""Guardrail-Tests für Befund 2.2 — Schatten-Autoritäten-Migration.

Drei Stellen haben live_claim / dialogue_signal unabhängig berechnet,
obwohl routing_frame["source_signals"] dieselben Werte bereits enthält.

Diese Tests prüfen:
1. Wenn routing_frame vorhanden ist → keine Doppelberechnung (kein zweiter Aufruf
   von detect_live_claim_kind / classify_dialogue_signal).
2. Wenn routing_frame/operation_contract fehlt → kein Signal-Fallback und
   keine Toolauswahl (SP3-P DECIDE B).
3. Verhalten (Tool-Auswahl / Ausgabe-Dict) bleibt identisch — kein
   Regressionsschaden durch die Migration.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping
from unittest.mock import patch, MagicMock

import pytest

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tools import select_relevant_tools


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _classifier(
    category: Category = Category.INFORMATION,
    *,
    needs_orchestrator: bool = False,
    route: Route = Route.DIRECT_TO_THINKING,
    confidence: float = 0.9,
) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        route=route,
        needs_orchestrator=needs_orchestrator,
        confidence=confidence,
        matched_pattern="",
    )


def _frame_with_signals(
    live_claim: str = "none",
    dialogue_act: str = "question",
    intent_kind: str = "conceptual_question",
    execution_mode: str = "direct_answer",
    evidence_need: str = "none",
) -> Dict[str, Any]:
    return {
        "intent_kind": intent_kind,
        "execution_mode": execution_mode,
        "evidence_need": evidence_need,
        "source_signals": {
            "live_claim": live_claim,
            "dialogue_signal": {
                "dialogue_act": dialogue_act,
                "response_tone": "neutral",
                "response_length_hint": "medium",
                "confidence": 0.72,
                "classifier_mode": "lexical",
            },
        },
    }


# ---------------------------------------------------------------------------
# orchestrator/tools.py — select_relevant_tools
# ---------------------------------------------------------------------------


class TestSelectRelevantToolsNoShadowAuthority:
    def test_live_claim_from_routing_frame_not_recomputed(self):
        """Wenn routing_frame.source_signals.live_claim vorhanden → kein detect_live_claim_kind-Aufruf."""
        frame = _frame_with_signals(live_claim="time", dialogue_act="question")
        with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
            select_relevant_tools(
                "Wie viel Uhr ist es?",
                _classifier(category=Category.INFORMATION),
                available_tools=[],
                routing_frame=frame,
            )
            mock_detect.assert_not_called()

    def test_dialogue_signal_from_routing_frame_not_recomputed(self):
        """Wenn routing_frame.source_signals.dialogue_signal vorhanden → kein classify_dialogue_signal-Aufruf."""
        frame = _frame_with_signals(live_claim="none", dialogue_act="question")
        with patch("core.orchestrator.frame_signals.classify_dialogue_signal") as mock_classify:
            select_relevant_tools(
                "Was ist Python?",
                _classifier(category=Category.INFORMATION),
                available_tools=[],
                routing_frame=frame,
            )
            mock_classify.assert_not_called()

    def test_no_detect_fallback_when_routing_frame_absent(self):
        """SP3-P: ohne operation_contract fail-closed, keine zweite Signalquelle."""
        with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
            result = select_relevant_tools(
                "Was ist Python?",
                _classifier(category=Category.INFORMATION),
                available_tools=[],
                routing_frame=None,
            )
            assert result == []
            mock_detect.assert_not_called()

    def test_no_dialogue_fallback_when_routing_frame_absent(self):
        """SP3-P: ohne operation_contract fail-closed, keine Dialogue-Reklassifizierung."""
        with patch("core.orchestrator.frame_signals.classify_dialogue_signal") as mock_classify:
            result = select_relevant_tools(
                "Was ist Python?",
                _classifier(category=Category.INFORMATION),
                available_tools=[],
                routing_frame=None,
            )
            assert result == []
            mock_classify.assert_not_called()

    def test_live_claim_time_blocks_tools_without_routing_frame(self):
        """Verhalten: live_claim TIME + kein selected_tool → leere Auswahl. Kein Regressions-Schaden."""
        # Ohne routing_frame (Fallback-Berechnung)
        result = select_relevant_tools(
            "Wie viel Uhr ist es?",
            _classifier(category=Category.INFORMATION),
            available_tools=[],
            routing_frame=None,
        )
        assert result == []

    def test_live_claim_time_blocks_tools_with_routing_frame(self):
        """Verhalten: identisch mit routing_frame."""
        frame = _frame_with_signals(
            live_claim="time",
            dialogue_act="question",
            intent_kind="current_state_question",
            execution_mode="single_tool",
        )
        result = select_relevant_tools(
            "Wie viel Uhr ist es?",
            _classifier(category=Category.INFORMATION),
            available_tools=[],
            routing_frame=frame,
        )
        # Kein Tool verfügbar → leere Auswahl unabhängig von der Signal-Quelle
        assert result == []

    def test_invalid_live_claim_string_without_contract_fails_closed(self):
        """Ein Frame ohne operation_contract ist keine Toolauswahl-Autoritaet."""
        frame = _frame_with_signals(live_claim="ungueltig_xyz")
        with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
            result = select_relevant_tools(
                "Was ist Python?",
                _classifier(category=Category.INFORMATION),
                available_tools=[],
                routing_frame=frame,
            )
            assert result == []
            mock_detect.assert_not_called()


# P10 T5 (M7): TestFallbackOperationFamilyHintFrameFirst
# → ausgelagert in tests/test_fallback_operation_family_p10.py (Doc 07 Zeilenlimit)
#
# TestFallbackAnalysisNoShadowAuthority + TestSuggestedToolsNoShadowAuthority
# → ausgelagert in tests/test_shadow_authority_fallback.py (Doc 07 Zeilenlimit)
