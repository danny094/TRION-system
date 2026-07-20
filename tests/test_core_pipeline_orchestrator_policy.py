import asyncio

from core.output.contracts import OutputResult
from core.pipeline import runner
from core.thinking.contracts import RiskLevel, ThinkingPlan
from tests._core_pipeline_request_helpers import core_pipeline_request


def test_core_complex_path_calls_orchestrator_and_exposes_conversation_policy(monkeypatch):
    seen = {}

    def classify_complex(user_text):
        from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel

        return ClassifierResult(
            category=Category.TOOL,
            safety_level=SafetyLevel.SAFE,
            needs_orchestrator=True,
            confidence=0.95,
            route=Route.NEEDS_ORCHESTRATOR,
            matched_pattern="tool",
            reason="complex path",
        )

    def fake_orchestrator(user_text, classifier_result, raw_tools=None, context_sources=None, conversation_id="", **kwargs):
        from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor

        seen["conversation_id"] = conversation_id
        return OrchestratorPackage(
            available_tools=[ToolDescriptor(name="memory_graph_search")],
            selected_tools=[ToolDescriptor(name="memory_graph_search")],
            context={
                "conversation_id": conversation_id,
                "conversation_policy": {
                    "memory_mode": "global_enabled",
                    "allow_global_memory_read": True,
                    "allow_long_term_write": True,
                },
            },
            classifier_result=classifier_result,
        )

    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        return OutputResult(content="complex answer")

    monkeypatch.setattr(runner, "classify", classify_complex)
    monkeypatch.setattr(
        runner,
        "build_plan",
        lambda user_text, classifier_result, **kwargs: ThinkingPlan(
            intent="answer_user",
            steps=[],
            needs_task_loop=False,
            risk_level=RiskLevel.SAFE,
            reasoning="deterministic test plan",
            suggested_tools=[],
            context_hints={"user_text": user_text},
            plan_id="plan-complex-policy",
        ),
    )

    response = asyncio.run(
        runner.run_chat(
            core_pipeline_request("Was weisst du ueber dieses Projekt?"),
            output_fn=fake_output,
            orchestrator_fn=fake_orchestrator,
        )
    )

    assert response.content == "complex answer"
    assert seen["conversation_id"] == "p0-test"
    assert seen["output_context"]["orchestrator"]["selected_tools"] == ["memory_graph_search"]
    assert seen["output_context"]["orchestrator"]["context"]["conversation_policy"]["memory_mode"] == "global_enabled"


def test_core_complex_path_passes_orchestrator_context_into_thinking(monkeypatch):
    seen = {}

    def classify_complex(user_text):
        from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel

        return ClassifierResult(
            category=Category.TOOL,
            safety_level=SafetyLevel.SAFE,
            needs_orchestrator=True,
            confidence=0.95,
            route=Route.NEEDS_ORCHESTRATOR,
            matched_pattern="tool",
            reason="complex path",
        )

    def fake_orchestrator(user_text, classifier_result, raw_tools=None, context_sources=None, conversation_id="", **kwargs):
        from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor

        return OrchestratorPackage(
            available_tools=[ToolDescriptor(name="request_container"), ToolDescriptor(name="memory_graph_search")],
            selected_tools=[ToolDescriptor(name="request_container")],
            context={
                "conversation_policy": {"memory_mode": "conversation_only"},
                "memory": {"available": True, "items": [{"id": "m1"}]},
            },
            classifier_result=classifier_result,
        )

    def fake_build_plan(user_text, classifier_result, orchestrator_context=None):
        seen["thinking_context"] = orchestrator_context
        return ThinkingPlan(
            intent="run_tools",
            steps=[],
            needs_task_loop=False,
            risk_level=RiskLevel.SAFE,
            reasoning="ok",
            suggested_tools=[],
            context_hints={"user_text": user_text},
            plan_id="plan-thinking-context",
        )

    async def fake_output(output_request, chat_request):
        return OutputResult(content="complex answer")

    monkeypatch.setattr(runner, "classify", classify_complex)
    monkeypatch.setattr(runner, "build_plan", fake_build_plan)

    response = asyncio.run(
        runner.run_chat(
            core_pipeline_request("Starte bitte den Container"),
            output_fn=fake_output,
            orchestrator_fn=fake_orchestrator,
        )
    )

    assert response.content == "complex answer"
    assert seen["thinking_context"]["available_tools"] == ["request_container", "memory_graph_search"]
    assert seen["thinking_context"]["selected_tools"] == ["request_container"]
    # P10 ergänzt routing_frame + self_context in context; exakte Gleichheit schlägt fehl.
    # Stattdessen: nur die vom Test kontrollierten Felder prüfen.
    ctx = seen["thinking_context"]["context"]
    assert ctx["conversation_policy"] == {"memory_mode": "conversation_only"}
    assert ctx["memory"] == {"available": True, "items": [{"id": "m1"}]}
    assert seen["thinking_context"]["available_tool_details"][0]["name"] == "request_container"
    assert seen["thinking_context"]["selected_tool_details"][0]["name"] == "request_container"
