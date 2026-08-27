from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.input_processor import chunk_document, estimate_input_tokens, is_long_document, process_long_input
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, TaskLoopSnapshot, TaskLoopState
from core.thinking.analyzer import analyze_request
from core.thinking.planner import build_plan_from_analysis
from core.thinking.prompts import build_thinking_prompt, reduce_document_context, reduce_orchestrator_context
from core.thinking.replanner import build_replan
from core.thinking.thinking import build_plan


def _classifier(needs_orchestrator: bool = False) -> ClassifierResult:
    return ClassifierResult(
        category=Category.TOOL if needs_orchestrator else Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING,
        matched_pattern="test",
        reason="test",
    )
def test_build_plan_uses_fallback_path_without_llm(monkeypatch):
    monkeypatch.setattr("core.thinking.analyzer.get_thinking_analyzer_enable", lambda: False)

    plan = build_plan("Hallo TRION", _classifier(False))

    assert plan.intent == "answer_user"
    assert plan.needs_task_loop is False
    assert plan.steps[0].step_id == "answer_user"


def test_build_plan_prefers_selected_tools_from_orchestrator_context(monkeypatch):
    monkeypatch.setattr("core.thinking.analyzer.get_thinking_analyzer_enable", lambda: False)

    plan = build_plan(
        "Starte den Container",
        _classifier(True),
        orchestrator_context={
            "available_tools": ["request_container", "memory_graph_search"],
            "selected_tools": ["request_container"],
            "context": {"conversation_policy": {"memory_mode": "conversation_only"}},
        },
    )

    assert plan.needs_task_loop is True
    assert plan.suggested_tools == ["request_container"]
    assert plan.steps[0].tool == "request_container"


def test_build_plan_does_not_force_memory_search_for_vague_keyword_request(monkeypatch):
    monkeypatch.setattr("core.thinking.analyzer.get_thinking_analyzer_enable", lambda: False)

    plan = build_plan(
        "Such dir die Suchbegriffe selber aus.",
        _classifier(True),
        orchestrator_context={
            "available_tools": ["memory_graph_search"],
            "selected_tools": ["memory_graph_search"],
        },
    )

    assert plan.needs_task_loop is False
    assert plan.suggested_tools == []
    assert plan.steps[0].step_id == "answer_user"


def test_build_plan_does_not_treat_memory_stats_request_as_graph_search(monkeypatch):
    monkeypatch.setattr("core.thinking.analyzer.get_thinking_analyzer_enable", lambda: False)

    plan = build_plan(
        "Sag mir welche Worte, Kategorien und Themen in deinen Memorys am häufigsten vorkommen.",
        _classifier(True),
        orchestrator_context={
            "available_tools": ["memory_graph_search", "memory_graph_stats"],
            "selected_tools": ["memory_graph_search"],
        },
    )

    assert plan.needs_task_loop is False
    assert plan.suggested_tools == []
    assert plan.steps[0].step_id == "answer_user"


def test_build_plan_resolves_container_arguments_from_verified_home_context(monkeypatch):
    monkeypatch.setattr("core.thinking.analyzer.get_thinking_analyzer_enable", lambda: False)

    plan = build_plan(
        "Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.",
        _classifier(True),
        orchestrator_context={
            "available_tools": ["container_inspect"],
            "selected_tools": ["container_inspect"],
            "selected_tool_details": [
                {
                    "name": "container_inspect",
                    "capability_required_args": ["container_id_or_name"],
                }
            ],
            "context": {
                "home_context": {
                    "verified": True,
                    "container_id": "abc123",
                    "container_name": "trion-home",
                }
            },
        },
    )

    assert plan.steps[0].tool == "container_inspect"
    assert plan.steps[0].tool_arguments == {"container_id": "abc123"}
