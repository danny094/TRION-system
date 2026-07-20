"""Shared ClassifierResult-Factory fuer Orchestrator-Tests.

Beide Orchestrator-Testdateien (Eligibility/Selection und Context-Policy)
brauchen denselben minimalen ClassifierResult-Stub - hier einmal definiert,
statt in jeder Datei dupliziert.
"""

from __future__ import annotations

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel


def make_classifier_result(
    *, needs_orchestrator: bool = True, category: Category = Category.TOOL
) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING,
        matched_pattern="test",
        reason="test classifier result",
    )
