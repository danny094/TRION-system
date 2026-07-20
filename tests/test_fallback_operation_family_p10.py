"""P10 T5: fallback/__init__.py liest requested_operation_family aus Frame.

Prüft das Fallback-Capsule-Muster in core/thinking/fallback/__init__.py:
- Frame-Wert ueberschreibt Textsignale
- Leerer Frame-Wert bleibt leer
- Kein Frame bleibt leer

Ausgelagert aus test_shadow_authority_migration.py (Doc 07 Zeilenlimit).
"""
from __future__ import annotations

from typing import Any, Dict

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        route=Route.DIRECT_TO_THINKING,
        needs_orchestrator=False,
        confidence=0.9,
        matched_pattern="",
    )


def _frame_with_signals(
    live_claim: str = "none",
    dialogue_act: str = "question",
) -> Dict[str, Any]:
    return {
        "intent_kind": "conceptual_question",
        "execution_mode": "direct_answer",
        "evidence_need": "none",
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


class TestFallbackOperationFamilyHintFrameFirst:
    """T5: fallback_analysis liest requested_operation_family nur aus dem Frame."""

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

    def test_operation_family_hint_from_frame_overrides_text_keywords(self):
        frame = _frame_with_signals()
        frame["requested_operation_family"] = "write"
        result = self._run("suche etwas im Speicher", frame)
        assert result["operation_family_hint"] == "write"

    def test_operation_family_hint_empty_frame_value_stays_empty(self):
        frame = _frame_with_signals()
        frame["requested_operation_family"] = ""
        result = self._run("suche etwas im Speicher", frame)
        assert result["operation_family_hint"] == ""

    def test_operation_family_hint_no_frame_stays_empty(self):
        result = self._run("lies die Datei", None)
        assert result["operation_family_hint"] == ""
