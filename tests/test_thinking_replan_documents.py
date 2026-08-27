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
def test_replanner_uses_analyzer_and_planner_path(monkeypatch):
    monkeypatch.setattr(
        "core.thinking.replanner.analyze_request",
        lambda *args, **kwargs: {
            "intent": "Retry deployment",
            "suggested_tools": ["request_container"],
            "reasoning": "Retry with a new container request.",
        },
    )
    snapshot = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="Deploy app",
        state=TaskLoopState.REPLANNING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        replan_count=1,
        max_replans=2,
        artifacts=[{"id": "artifact-1"}],
    )
    failure = StepExecutionResult(step_id="tool_1", status=StepExecutionStatus.FAILED, error="boom")

    plan = build_replan(
        build_plan_from_analysis({"intent": "Deploy app", "suggested_tools": ["request_container"]}, user_text="Deploy app"),
        objective="Deploy app",
        failed_step_id="tool_1",
        failure=failure,
        snapshot=snapshot,
    )

    assert plan.intent == "Retry deployment"
    assert plan.steps[0].tool == "request_container"
    assert plan.context_hints["replan"]["failed_step_id"] == "tool_1"


def test_planner_creates_workspace_get_steps_for_document_chunks():
    document = process_long_input(
        "Inhaltsverzeichnis\nKapitel 1 ..... 1\nKapitel 2 ..... 5\nKapitel 3 ..... 8\n\n" + " ".join(f"token{i}" for i in range(12)),
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 100,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=5,
        overlap_tokens=1,
    )
    plan = build_plan_from_analysis(
        {
            "intent": "Inspect uploaded document",
            "suggested_tools": ["workspace_get"],
            "document_retrieval_mode": "structure_first",
        },
        user_text="Inspect uploaded document",
        classifier_result=_classifier(True),
        document_context=document,
    )

    assert plan.needs_task_loop is True
    assert len(plan.steps) >= 1
    assert plan.steps[0].tool == "workspace_get"
    assert plan.steps[0].tool_arguments["entry_id"] == 100
    assert plan.context_hints["document_retrieval_mode"] == "structure_first"


def test_planner_prefers_semantic_then_workspace_for_document_question():
    document = process_long_input(
        " ".join(f"token{i}" for i in range(12)),
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 100,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=5,
        overlap_tokens=1,
    )
    plan = build_plan_from_analysis(
        {
            "intent": "What does the uploaded document say about deployment?",
            "suggested_tools": ["memory_semantic_search", "workspace_get"],
            "document_retrieval_mode": "semantic_first",
        },
        user_text="What does the uploaded document say about deployment?",
        classifier_result=_classifier(True),
        document_context=document,
    )

    assert plan.steps[0].tool == "memory_semantic_search"
    assert plan.steps[1].tool == "workspace_get"
    assert plan.context_hints["document_retrieval_mode"] == "semantic_first"


def test_planner_uses_index_candidates_before_generic_workspace_chunks():
    document = process_long_input(
        "Inhaltsverzeichnis\nKapitel 1 ..... 1\nKapitel 2 ..... 5\n\n"
        "Kapitel 1 Text\nMehr Text\n\nKapitel 2 Text\nMehr Text",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 10,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=40,
        overlap_tokens=5,
    )
    plan = build_plan_from_analysis(
        {
            "intent": "List chapters in the uploaded document",
            "suggested_tools": ["workspace_get", "memory_semantic_search"],
            "document_retrieval_mode": "structure_first",
        },
        user_text="List chapters in the uploaded document",
        classifier_result=_classifier(True),
        document_context=document,
    )

    expected_ids = document.index_like_entry_ids[:3]

    assert plan.steps[0].tool == "workspace_get"
    assert [step.tool_arguments["entry_id"] for step in plan.steps[: len(expected_ids)]] == expected_ids
    assert "document_source_step" not in plan.steps[0].tool_arguments
    assert plan.steps[-1].tool == "memory_semantic_search"


def test_planner_limits_structure_overview_reads_to_two_chunks():
    seen = {"entry_id": 19}

    def save_workspace(*_args):
        seen["entry_id"] += 1
        return seen["entry_id"]

    document = process_long_input(
        "Inhaltsverzeichnis\nKapitel 1 ..... 1\nKapitel 2 ..... 5\nKapitel 3 ..... 8\n\n"
        "Kapitel 1 Text\nMehr Text\n\nKapitel 2 Text\nMehr Text\n\nKapitel 3 Text",
        conversation_id="conv-1",
        workspace_save_fn=save_workspace,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=25,
        overlap_tokens=5,
    )
    plan = build_plan_from_analysis(
        {
            "intent": "How many chapters are in the uploaded document?",
            "suggested_tools": ["workspace_get", "memory_semantic_search"],
            "document_retrieval_mode": "structure_first",
        },
        user_text="How many chapters are in the uploaded document?",
        classifier_result=_classifier(True),
        document_context=document,
    )

    workspace_steps = [step for step in plan.steps if step.tool == "workspace_get"]

    assert 1 <= len(workspace_steps) <= 2
    assert [step.tool_arguments["entry_id"] for step in workspace_steps] == document.index_like_entry_ids[: len(workspace_steps)]


def test_planner_limits_semantic_follow_up_reads_to_chapter_candidates():
    document = process_long_input(
        "Inhaltsverzeichnis\nKapitel 1 ..... 1\nKapitel 2 ..... 5\nKapitel 3 ..... 8\n\n"
        "Kapitel 1 Text\nMehr Text\n\nKapitel 2 Text\nMehr Text\n\nKapitel 3 Text",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 7,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=25,
        overlap_tokens=5,
    )
    plan = build_plan_from_analysis(
        {
            "intent": "What does the uploaded document say about chapter 2?",
            "suggested_tools": ["memory_semantic_search", "workspace_get"],
            "document_retrieval_mode": "semantic_first",
        },
        user_text="What does the uploaded document say about chapter 2?",
        classifier_result=_classifier(True),
        document_context=document,
    )

    workspace_steps = [step for step in plan.steps if step.tool == "workspace_get"]

    assert plan.steps[0].tool == "memory_semantic_search"
    assert 1 <= len(workspace_steps) <= 3
    assert [step.tool_arguments["entry_id"] for step in workspace_steps] == document.chapter_candidate_entry_ids[: len(workspace_steps)]
    assert workspace_steps[0].tool_arguments["document_source_step"] == "semantic_search_1"
