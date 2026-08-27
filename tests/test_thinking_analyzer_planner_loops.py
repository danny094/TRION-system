from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.classifier.classifier import classify
from core.input_processor import chunk_document, estimate_input_tokens, is_long_document, process_long_input
from core.routing_frame.builder import build_routing_frame
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
def test_analyzer_parses_llm_json_when_enabled():
    async def fake_complete_prompt(**kwargs):
        return """
        ```json
        {"intent":"Deploy app","suggested_tools":["request_container"],"task_loop_candidate":true,"needs_loop":true,"repeat_count_hint":3,"operation_family_hint":"inspect","reasoning":"Use a container."}
        ```
        """

    raw = analyze_request(
        "Deploy the app",
        _classifier(True),
        complete_prompt_fn=fake_complete_prompt,
        llm_enabled=True,
    )

    assert raw["intent"] == "Deploy app"
    assert raw["suggested_tools"] == ["request_container"]
    assert raw["needs_loop"] is True
    assert raw["repeat_count_hint"] == 3
    assert raw["operation_family_hint"] == "inspect"


def test_planner_creates_task_loop_plan_from_suggested_tools():
    plan = build_plan_from_analysis(
        {
            "intent": "Deploy app",
            "suggested_tools": ["request_container", "container_logs"],
            "reasoning": "Two tool steps are required.",
            "hallucination_risk": "medium",
        },
        user_text="Deploy the app",
        classifier_result=_classifier(True),
    )

    assert plan.needs_task_loop is True
    assert [step.tool for step in plan.steps] == ["request_container", "container_logs"]
    assert plan.context_hints["classifier_route"] == "needs_orchestrator"


def test_planner_expands_single_tool_loop_from_routing_frame_repeat_count():
    plan = build_plan_from_analysis(
        {
            "intent": "Teste die Suche mehrfach",
            "suggested_tools": ["memory_graph_search"],
            "reasoning": "Repeated execution requested.",
            "task_loop_kind": "loop",
            "task_loop_confidence": 0.9,
            "estimated_steps": 5,
        },
        user_text="Teste die Suche 5x",
        classifier_result=_classifier(True),
        orchestrator_context={
            "context": {
                "routing_frame": {
                    "execution_mode": "loop",
                    "source_signals": {"repeat_count": 5},
                }
            }
        },
    )

    assert plan.needs_task_loop is True
    assert len(plan.steps) == 5
    assert all(step.tool == "memory_graph_search" for step in plan.steps)
    assert plan.steps[0].title == "Attempt 1: Use memory_graph_search"
    assert plan.context_hints["routing_execution_mode"] == "loop"
    assert plan.context_hints["estimated_steps"] == 5


def test_planner_expands_single_tool_loop_from_thinking_hint_without_routing_repeat():
    plan = build_plan_from_analysis(
        {
            "intent": "Führe 3 Suchen aus",
            "suggested_tools": ["memory_graph_search"],
            "reasoning": "Repeated execution requested.",
            "task_loop_kind": "loop",
            "task_loop_confidence": 0.9,
            "needs_loop": True,
            "repeat_count_hint": 3,
            "estimated_steps": 3,
        },
        user_text="Führe 3 Memory-Suchen aus",
        classifier_result=_classifier(True),
        orchestrator_context={"context": {"routing_frame": {"execution_mode": "retrieve_context"}}},
    )

    assert plan.needs_task_loop is True
    assert len(plan.steps) == 3
    assert all(step.tool == "memory_graph_search" for step in plan.steps)
    assert plan.context_hints["needs_loop"] is True
    assert plan.context_hints["repeat_count_hint"] == 3


def test_planner_backfills_selected_tool_when_llm_loop_hint_omits_suggested_tools():
    user_text = 'Führe 3 Memory-Suchen aus: "Python", "Projekt", "Name".'
    routing_frame = build_routing_frame(user_text, classify(user_text))

    assert routing_frame["operation_contract"]["target"] == "Python"
    assert routing_frame["operation_contract"]["targets"] == ("Python", "Projekt", "Name")

    plan = build_plan_from_analysis(
        {
            "intent": "3 Memory-Suchen ausführen",
            "suggested_tools": [],
            "reasoning": "User requested repeated searches.",
            "task_loop_kind": "loop",
            "task_loop_confidence": 0.9,
            "needs_loop": True,
            "repeat_count_hint": 3,
            "estimated_steps": 3,
        },
        user_text=user_text,
        classifier_result=_classifier(True),
        orchestrator_context={
            "selected_tools": ["memory_graph_search"],
            "selected_tool_details": [{"name": "memory_graph_search", "capability_required_args": ["query"]}],
            "context": {"routing_frame": routing_frame},
        },
    )

    assert plan.intent == "3 Memory-Suchen ausführen"
    assert plan.suggested_tools == ["memory_graph_search"]
    assert plan.needs_task_loop is True
    assert [step.tool for step in plan.steps] == ["memory_graph_search", "memory_graph_search", "memory_graph_search"]
    assert [step.tool_arguments["query"] for step in plan.steps] == ["Python", "Projekt", "Name"]
