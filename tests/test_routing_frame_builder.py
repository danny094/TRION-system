"""Guardrail tests for core.routing_frame.builder.build_routing_frame.

These tests call build_routing_frame directly (not via the pipeline stage)
to pin the behaviour of each private helper before the builder.py package
split.  After the split the same import path resolves via __init__.py, so
these tests act as a regression net for the restructuring.
"""

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.routing_frame.builder import build_routing_frame


def _classifier(
    category: Category = Category.INFORMATION,
    *,
    needs_orchestrator: bool = False,
    route: Route | None = None,
    confidence: float = 0.9,
) -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=confidence,
        route=route or (Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING),
        matched_pattern="test",
        reason="test",
    )


def _tool(name: str) -> dict:
    return {"name": name, "capability_domain": "general", "capability_operation": "read"}


# --- _intent_kind branches ---


def test_intent_kind_meta_analysis_for_pipeline_token():
    frame = build_routing_frame(
        "Zeige mir den classifier trace fuer diese Anfrage.",
        _classifier(),
    )
    assert frame["intent_kind"] == "meta_analysis"
    assert frame["evidence_need"] == "none"


def test_intent_kind_meta_analysis_for_orchestrator_token():
    frame = build_routing_frame(
        "Was macht der orchestrator gerade?",
        _classifier(),
    )
    assert frame["intent_kind"] == "meta_analysis"


def test_intent_kind_task_loop_request_for_mehrfach_marker():
    frame = build_routing_frame(
        "Pruefe das mehrfach und sag mir am Ende Bescheid.",
        _classifier(needs_orchestrator=True),
        selected_tool_details=[_tool("container_inspect")],
    )
    assert frame["intent_kind"] == "task_loop_request"
    assert frame["execution_mode"] == "loop"


def test_intent_kind_action_request_for_tool_category():
    frame = build_routing_frame(
        "Fuehre die Transformation aus.",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    assert frame["intent_kind"] == "action_request"


def test_intent_kind_action_request_for_planning_category():
    frame = build_routing_frame(
        "Erstelle einen Migrationsplan.",
        _classifier(Category.PLANNING, needs_orchestrator=True),
    )
    assert frame["intent_kind"] == "action_request"


def test_intent_kind_conceptual_question_is_default():
    frame = build_routing_frame(
        "Erklaere mir das Konzept der Versionierung.",
        _classifier(),
    )
    assert frame["intent_kind"] == "conceptual_question"
    assert frame["execution_mode"] == "direct_answer"
    assert frame["evidence_need"] == "none"


# --- _domain branches ---


def test_domain_memory_for_memory_token():
    frame = build_routing_frame(
        "Suche im memory nach meinem letzten Projekt.",
        _classifier(),
    )
    assert frame["domain"] == "memory"


def test_domain_memory_for_erinner_token():
    frame = build_routing_frame(
        "Erinnerst du dich an das letzte Gespraech?",
        _classifier(),
    )
    assert frame["domain"] == "memory"


def test_domain_time_for_time_live_claim():
    frame = build_routing_frame(
        "Wie viel Uhr ist es gerade?",
        _classifier(),
    )
    assert frame["domain"] == "time"
    assert frame["evidence_need"] == "live_runtime"


def test_domain_general_for_neutral_text():
    frame = build_routing_frame(
        "Erklaere mir das Konzept der Versionierung.",
        _classifier(),
    )
    assert frame["domain"] == "general"


# --- _execution_mode branches ---


def test_execution_mode_refuse_for_blocked_route():
    frame = build_routing_frame(
        "Loesche alle Daten.",
        _classifier(route=Route.BLOCK),
    )
    assert frame["execution_mode"] == "refuse"


def test_execution_mode_single_tool_for_one_selected_tool():
    frame = build_routing_frame(
        "Wie viel Uhr ist es?",
        _classifier(needs_orchestrator=True),
        selected_tool_details=[_tool("time_now")],
    )
    assert frame["execution_mode"] == "single_tool"


def test_execution_mode_multi_tool_plan_for_two_selected_tools():
    frame = build_routing_frame(
        "Pruefe den Container und speichere das Ergebnis.",
        _classifier(needs_orchestrator=True),
        selected_tool_details=[_tool("container_inspect"), _tool("memory_save")],
    )
    assert frame["execution_mode"] == "multi_tool_plan"


def test_execution_mode_retrieve_context_for_action_request_without_tools():
    frame = build_routing_frame(
        "Fuehre die Aufgabe aus.",
        _classifier(Category.TOOL, needs_orchestrator=True),
    )
    assert frame["execution_mode"] == "retrieve_context"


# --- _repeat_count branches ---


def test_repeat_count_extracted_from_3x():
    frame = build_routing_frame(
        "Pruefe den Status 3x.",
        _classifier(needs_orchestrator=True),
        selected_tool_details=[_tool("container_inspect")],
    )
    assert frame["source_signals"]["repeat_count"] == 3


def test_repeat_count_extracted_from_2x():
    frame = build_routing_frame(
        "Versuche das 2x.",
        _classifier(needs_orchestrator=True),
        selected_tool_details=[_tool("container_inspect")],
    )
    assert frame["source_signals"]["repeat_count"] == 2


def test_repeat_count_defaults_to_1_without_marker():
    frame = build_routing_frame(
        "Pruefe den Status.",
        _classifier(),
    )
    assert frame["source_signals"]["repeat_count"] == 1
    assert isinstance(frame["confidence"], float)
