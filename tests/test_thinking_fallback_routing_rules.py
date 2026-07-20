"""Doc 36 Regel 6 — Regression für requires_also-Pfad in _apply_fallback_routing_rules.

Ausgelagert aus test_thinking_fallback.py (Doc07 200-Zeilen-Cap, P11 SP3-H —
die SP3-H-Korrektur dieser beiden Tests hätte test_thinking_fallback.py über
das Limit gehoben, daher eigene Datei statt Grandfathering der Vorab-Größe).
(PIANO 1.0 B3-Vollfix, 2026-06-12)
"""
from __future__ import annotations

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.thinking.fallback import fallback_analysis


def _classifier(category: Category, *, needs_orchestrator: bool = False, pattern: str = "test") -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING,
        matched_pattern=pattern,
        reason="test",
    )


def test_fallback_routing_rules_requires_also_matches_when_both_conditions_met():
    """P11 SP3-H: routing_frame vorhanden (Pipeline lief) + leeres selected
    → requires_also-Regel darf NICHT mehr auf available zugreifen, auch wenn
    beide Bedingungen matchen. Vorher (Bug): first_available lieferte
    memory_retrieve zurueck, obwohl die Eligibility-Gate nichts freigegeben
    hat — Schatten-Autoritaet (siehe test_thinking_no_ungated_tools.py)."""
    raw = fallback_analysis(
        "Prüfe den Kontext.",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "memory_retrieve"}, {"name": "memory_save"}],
        selected_tools=[],
        orchestrator_context={
            "routing_frame": {
                "execution_mode": "retrieve_context",
                "evidence_need": "memory_context",
            }
        },
        document_context=None,
    )
    assert raw["suggested_tools"] == []


def test_fallback_routing_rules_requires_also_blocks_when_secondary_condition_fails():
    """retrieve_context aber falsches evidence_need → requires_also schlägt fehl, keine Auswahl."""
    raw = fallback_analysis(
        "Prüfe den Kontext.",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "memory_retrieve"}, {"name": "memory_save"}],
        selected_tools=[],
        orchestrator_context={
            "routing_frame": {
                "execution_mode": "retrieve_context",
                "evidence_need": "web_search",
            }
        },
        document_context=None,
    )
    assert raw["suggested_tools"] == []
