"""Fallback-Keyword-Pfade fuer Tool-Vorschlaege ohne Operation-Hint.

Ausgelagert aus test_thinking_fallback.py (Doc07 200-Zeilen-Cap, P11 SP3-H —
die SP3-H-Korrektur eines anderen Tests in der Ursprungsdatei hätte sie über
das Limit gehoben; die ursprüngliche Datei war bereits vor SP3-H bei 348
Zeilen, daher echter Split statt Grandfathering).
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


def test_operation_family_hint_does_not_use_search_keyword():
    raw = fallback_analysis(
        "Suche nach dem Schluesselwort im Memory.",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["operation_family_hint"] == ""


def test_operation_family_hint_does_not_use_read_keyword():
    raw = fallback_analysis(
        "Zeige mir die aktuellen Logs.",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["operation_family_hint"] == ""


def test_operation_family_hint_does_not_use_inspect_keyword():
    raw = fallback_analysis(
        "Pruefe den Status des Containers.",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["operation_family_hint"] == ""


def test_operation_family_hint_does_not_use_write_keyword():
    raw = fallback_analysis(
        "Speichere das Ergebnis im Projekt.",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["operation_family_hint"] == ""


def test_operation_family_hint_does_not_use_delete_keyword():
    raw = fallback_analysis(
        "Loesche die alte Datei aus dem Projekt.",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["operation_family_hint"] == ""


def test_operation_family_hint_does_not_use_time_now_tool():
    raw = fallback_analysis(
        "Wie viel Uhr ist es?",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "time_now"}],
        selected_tools=[{"name": "time_now"}],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == ["time_now"]
    assert raw["operation_family_hint"] == ""


def test_operation_family_hint_empty_when_no_keyword_and_no_tools():
    raw = fallback_analysis(
        "Erzaehl mir einen Witz.",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["operation_family_hint"] == ""


def test_fallback_explains_requested_loop_without_executable_tools():
    raw = fallback_analysis(
        "Pruefe das 5x und probiere das naechste.",
        _classifier(Category.INFORMATION, needs_orchestrator=True, pattern="loop"),
        available_tools=[],
        selected_tools=[],
        orchestrator_context={
            "routing_frame": {
                "execution_mode": "loop",
                "source_signals": {"repeat_count": 5},
            }
        },
        document_context=None,
    )
    assert raw["task_loop_candidate"] is False
    assert raw["task_loop_kind"] == "none"
    assert "no executable tools" in raw["task_loop_reason"]


def test_fallback_suggests_request_container_for_container_keyword():
    # "deploy" ist in CONTAINER_KW, aber nicht in _CONTAINER_TOKENS von live_claims →
    # live_claim bleibt NONE und der Keyword-Pfad in tools.py:118 greift.
    raw = fallback_analysis(
        "Deploy die neue Komponente.",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "request_container"}],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == ["request_container"]


def test_fallback_suggests_memory_save_for_save_keyword():
    raw = fallback_analysis(
        "Merke dir diesen Hinweis.",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "memory_save"}],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == ["memory_save"]


def test_fallback_suggests_memory_graph_search_for_recall_keyword():
    raw = fallback_analysis(
        "Erinnerst du dich an das Projekt?",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "memory_graph_search"}],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == ["memory_graph_search"]
