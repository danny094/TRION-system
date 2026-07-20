from core.thinking.planner import build_plan_from_analysis
from tests.test_documententest_support import document_context_from_fixture


def test_documententest_followup_question_uses_find_then_read_plan():
    document = document_context_from_fixture()
    plan = build_plan_from_analysis(
        {
            "intent": "Wie viele Kapitel hat diese Geschichte?",
            "suggested_tools": ["workspace_get", "memory_semantic_search"],
            "document_retrieval_mode": "structure_first",
        },
        user_text="Wie viele Kapitel hat diese Geschichte?",
        document_context=document,
    )

    workspace_steps = [step for step in plan.steps if step.tool == "workspace_get"]

    assert document.index_like_entry_ids
    assert plan.needs_task_loop is True
    assert workspace_steps
    assert [step.tool_arguments["entry_id"] for step in workspace_steps] == document.index_like_entry_ids[: len(workspace_steps)]
    assert plan.steps[-1].tool == "memory_semantic_search"


def test_documententest_semantic_followup_starts_with_search_then_reads_candidates():
    document = document_context_from_fixture()
    plan = build_plan_from_analysis(
        {
            "intent": "Was passiert in PREGO!?",
            "suggested_tools": ["memory_semantic_search", "workspace_get"],
            "document_retrieval_mode": "semantic_first",
        },
        user_text="Was passiert in PREGO!?",
        document_context=document,
    )

    workspace_steps = [step for step in plan.steps if step.tool == "workspace_get"]

    assert plan.needs_task_loop is True
    assert plan.steps[0].tool == "memory_semantic_search"
    assert workspace_steps
    assert len(workspace_steps) <= 3
    assert [step.tool_arguments["entry_id"] for step in workspace_steps] == document.chapter_candidate_entry_ids[: len(workspace_steps)]
