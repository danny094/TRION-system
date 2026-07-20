"""Schatten-Autoritäten-Migration: fallback/__init__.py + fallback/tools.py.

Ausgelagert aus test_shadow_authority_migration.py (Doc 07 Zeilenlimit).
Prüft dass fallback_analysis und suggested_tools nach PIANO keine Doppelberechnung
von classify_dialogue_signal / detect_live_claim_kind durchführen, wenn der
routing_frame bereits die Signale enthält.
"""
from __future__ import annotations

from typing import Any, Dict
from unittest.mock import patch, MagicMock

import pytest

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.classifier.live_claims import LiveClaimKind
from core.dialogue_signal.contracts import DialogueSignal


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
# fallback/__init__.py — fallback_analysis
# ---------------------------------------------------------------------------


class TestFallbackAnalysisNoShadowAuthority:
    def _run(self, user_text: str, frame: Dict[str, Any] | None) -> Dict:
        from core.thinking.fallback import fallback_analysis
        orchestrator_context = {"routing_frame": frame} if frame is not None else {}
        return fallback_analysis(
            user_text,
            _classifier(),
            available_tools=[],
            selected_tools=[],
            orchestrator_context=orchestrator_context,
            document_context=None,
        )

    def test_dialogue_signal_from_routing_frame_not_recomputed(self):
        """Wenn frame.source_signals.dialogue_signal vorhanden → kein classify_dialogue_signal-Aufruf."""
        frame = _frame_with_signals(dialogue_act="question")
        with patch("core.orchestrator.frame_signals.classify_dialogue_signal") as mock_classify:
            self._run("Was ist Python?", frame)
            mock_classify.assert_not_called()

    def test_fallback_to_classify_when_frame_empty(self):
        """Wenn kein frame → classify_dialogue_signal WIRD aufgerufen."""
        with patch("core.orchestrator.frame_signals.classify_dialogue_signal") as mock_classify:
            mock_classify.return_value = DialogueSignal("question", "neutral", "medium", 0.72)
            self._run("Was ist Python?", None)
            mock_classify.assert_called_once()

    def test_response_tone_from_routing_frame(self):
        """response_tone kommt aus routing_frame, nicht aus Neuberechnung."""
        frame = _frame_with_signals(dialogue_act="feedback")
        frame["source_signals"]["dialogue_signal"]["response_tone"] = "mirror_user"
        result = self._run("Das war zu hart formuliert.", frame)
        assert result["response_tone"] == "mirror_user"

    def test_dialogue_act_from_routing_frame_in_output(self):
        """dialogue_act im Output-Dict spiegelt den routing_frame-Wert wider."""
        frame = _frame_with_signals(dialogue_act="ack")
        frame["source_signals"]["dialogue_signal"]["response_length_hint"] = "short"
        result = self._run("Okey.", frame)
        assert result["dialogue_act"] == "ack"
        assert result["response_length_hint"] == "short"


# ---------------------------------------------------------------------------
# fallback/tools.py — suggested_tools
# ---------------------------------------------------------------------------


class TestSuggestedToolsNoShadowAuthority:
    def _run(
        self,
        lowered: str,
        frame: Dict[str, Any],
        available: list | None = None,
        selected: list | None = None,
    ) -> list:
        from core.thinking.fallback.tools import suggested_tools
        orchestrator_context = {"routing_frame": frame}
        return suggested_tools(
            lowered,
            available or [],
            selected or [],
            _classifier(),
            None,
            orchestrator_context,
            None,
        )

    def test_live_claim_from_frame_not_recomputed(self):
        """Wenn frame.source_signals.live_claim vorhanden → kein detect_live_claim_kind-Aufruf."""
        frame = _frame_with_signals(live_claim="time")
        with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
            self._run("wie viel uhr ist es?", frame)
            mock_detect.assert_not_called()

    def test_fallback_to_detect_when_frame_empty(self):
        """Wenn kein live_claim in source_signals → detect_live_claim_kind WIRD aufgerufen."""
        with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
            mock_detect.return_value = LiveClaimKind.NONE
            from core.thinking.fallback.tools import suggested_tools
            suggested_tools("was ist python?", [], [], _classifier(), None, {}, None)
            mock_detect.assert_called_once()

    def test_live_claim_time_blocks_empty_selection(self):
        """live_claim TIME + kein selected_tool → leere Auswahl. Verhalten unverändert."""
        frame = _frame_with_signals(live_claim="time")
        result = self._run("wie viel uhr ist es?", frame, available=["time_now"])
        assert result == []

    def test_live_claim_none_with_routing_frame_blocks_keyword_selection(self):
        """P11 SP3-H: routing_frame vorhanden (Pipeline lief) + leeres selected
        → KEINE Keyword-Auswahl auf available, auch wenn live_claim NONE ist.
        Vorher (Bug): Keyword-Match auf available_tools lieferte ["memory_save"]
        zurueck, obwohl die Eligibility-Gate keine Tools freigegeben hat —
        Schatten-Autoritaet. Siehe test_thinking_no_ungated_tools.py."""
        frame = _frame_with_signals(
            live_claim="none",
            intent_kind="action_request",
            execution_mode="single_tool",
        )
        result = self._run(
            "speichere diesen fakt.",
            frame,
            available=["memory_save"],
            selected=[],
        )
        assert result == []

    def test_invalid_live_claim_falls_back_gracefully(self):
        """Ungültiger live_claim-String → Fallback, kein Crash."""
        frame = _frame_with_signals(live_claim="totally_invalid")
        with patch("core.orchestrator.frame_signals.detect_live_claim_kind") as mock_detect:
            mock_detect.return_value = LiveClaimKind.NONE
            result = self._run("was ist python?", frame)
            mock_detect.assert_called_once()
