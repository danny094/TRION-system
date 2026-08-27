from core.task_loop.executor import build_tool_call
from core.thinking.planner import build_plan_from_analysis
from tests.document_embedding_support import (
    index_document_for_embedding_search,
    load_embedding_tools,
    require_embedding_runtime,
)
from tests.verifier_document_fixture_support import document_context, entry_id_for_phrase


def test_live_embedding_search_finds_police_chunk_for_synthetic_story(monkeypatch, tmp_path):
    require_embedding_runtime()
    semantic_save_tool, semantic_search_tool = load_embedding_tools(monkeypatch, tmp_path)
    conversation_id = "embed-synthetic-neighborhood"
    expected_entry = entry_id_for_phrase("synthetic_neighborhood_story.md", "hatte sie schon die Polizei verständigt")

    index_document_for_embedding_search("synthetic_neighborhood_story.md", semantic_save_tool, conversation_id)
    result = semantic_search_tool(
        query="Warum ruft die Frau die Polizei?",
        conversation_id=conversation_id,
        content_type="document_chunk",
    )

    resolved_entry_ids = [
        int(part.partition(":")[2])
        for item in result.get("results") or []
        for part in str((item.get("metadata") or {}).get("value") or "").split(";")
        if part.startswith("workspace_entry_id:")
    ]

    assert expected_entry > 0
    assert resolved_entry_ids
    assert expected_entry in resolved_entry_ids[:3]


def test_live_embedding_search_drives_workspace_resolution_for_ki_risk_question(monkeypatch, tmp_path):
    require_embedding_runtime()
    semantic_save_tool, semantic_search_tool = load_embedding_tools(monkeypatch, tmp_path)
    conversation_id = "embed-ki-risiken"
    question = "Welche Risiken generativer KI beschreibt der Text?"
    expected_entry = entry_id_for_phrase("synthetic_ai_safety_guide.md", "Generative KI-Tools eröffnen neue Anwen")
    document = document_context("synthetic_ai_safety_guide.md")

    index_document_for_embedding_search("synthetic_ai_safety_guide.md", semantic_save_tool, conversation_id)
    plan = build_plan_from_analysis(
        {
            "intent": question,
            "suggested_tools": ["memory_semantic_search", "workspace_get"],
            "document_retrieval_mode": "semantic_first",
        },
        user_text=question,
        document_context=document,
    )
    result = semantic_search_tool(
        query=question,
        conversation_id=conversation_id,
        content_type="document_chunk",
    )

    resolved = build_tool_call(
        next(step for step in plan.steps if step.tool == "workspace_get"),
        artifacts=[
            {
                "artifact_type": "semantic_search_result",
                "source_step_id": "semantic_search_1",
                "rank": rank,
                "workspace_entry_id": int(part.partition(":")[2]),
            }
            for rank, item in enumerate(result.get("results") or [])
            for part in str((item.get("metadata") or {}).get("value") or "").split(";")
            if part.startswith("workspace_entry_id:")
        ],
    )

    assert expected_entry > 0
    assert resolved.arguments["entry_id"] == expected_entry
