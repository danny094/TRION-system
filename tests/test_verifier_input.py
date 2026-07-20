from core.input_processor.contracts import DocumentContext
from core.thinking.contracts import ThinkingPlan, RiskLevel, PlanStep
from core.verifier.input_prepare import build_verifier_input


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect_document",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="",
        plan_id="verify-plan-1",
    )


def test_build_verifier_input_uses_raw_excerpt_for_normal_input(monkeypatch):
    monkeypatch.setattr("core.verifier.input_prepare.get_control_prompt_user_chars", lambda: 20)

    result = build_verifier_input("Hallo TRION, das ist kurz.", _plan(), document_context=None)

    assert result.document_mode == "normal"
    assert result.document_summary == ""
    assert result.user_excerpt == "Hallo TRION, das ist"


def test_build_verifier_input_prefers_document_summary_for_long_input(monkeypatch):
    monkeypatch.setattr("core.verifier.input_prepare.get_control_prompt_user_chars", lambda: 30)
    document = DocumentContext(
        conversation_id="conv-1",
        summary="Dokumentzusammenfassung fuer Planning: Kapitel und Inhaltsverzeichnis",
        key_facts=["Kapitel vorhanden"],
        total_chunks=4,
        workspace_entry_ids=[1, 2, 3, 4],
        preferred_entry_ids=[1, 2],
        index_like_entry_ids=[1],
        chapter_candidate_entry_ids=[1, 2],
        original_char_count=12000,
        semantic_keys=["document_chunk_0"],
        semantic_candidate_keys=["document_chunk_0"],
    )

    result = build_verifier_input("Rohtext", _plan(), document_context=document)

    assert result.document_mode == "long_document"
    assert result.document_summary == document.summary[:30]
    assert result.user_excerpt == document.summary[:30]
    assert result.document_meta["total_chunks"] == 4
    assert result.document_meta["preferred_entry_ids"] == [1, 2]
    assert result.document_meta["index_like_entry_ids"] == [1]
    assert result.document_meta["chapter_candidate_entry_ids"] == [1, 2]
    assert result.document_meta["question_focus"] == "semantic"
    assert result.document_meta["structure_required"] is False
    assert result.document_meta["document_retrieval_mode"] == "none"
    assert result.document_meta["plan_id"] == "verify-plan-1"


def test_build_verifier_input_marks_structure_focus_for_chapter_question(monkeypatch):
    monkeypatch.setattr("core.verifier.input_prepare.get_control_prompt_user_chars", lambda: 30)
    document = DocumentContext(
        conversation_id="conv-1",
        summary="Dokumentzusammenfassung fuer Planning: Kapitel und Inhaltsverzeichnis",
        key_facts=["Kapitel vorhanden"],
        total_chunks=4,
        workspace_entry_ids=[1, 2, 3, 4],
        preferred_entry_ids=[1, 2],
        index_like_entry_ids=[1],
        chapter_candidate_entry_ids=[1, 2],
        original_char_count=12000,
        semantic_keys=["document_chunk_0"],
        semantic_candidate_keys=["document_chunk_0"],
    )
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="",
        context_hints={"document_retrieval_mode": "structure_first"},
        plan_id="verify-plan-2",
    )

    result = build_verifier_input("Wie viele Kapitel hat diese Geschichte?", plan, document_context=document)

    assert result.document_meta["question_focus"] == "structure"
    assert result.document_meta["structure_required"] is True


def test_build_verifier_input_includes_compact_retrieval_plan(monkeypatch):
    monkeypatch.setattr("core.verifier.input_prepare.get_control_prompt_user_chars", lambda: 30)
    document = DocumentContext(
        conversation_id="conv-1",
        summary="Dokumentzusammenfassung fuer Planning: Kapitel und Inhaltsverzeichnis",
        key_facts=["Kapitel vorhanden"],
        total_chunks=4,
        workspace_entry_ids=[1, 2, 3, 4],
        preferred_entry_ids=[1, 2],
        index_like_entry_ids=[1],
        chapter_candidate_entry_ids=[1, 2],
        original_char_count=12000,
        semantic_keys=["document_chunk_0"],
        semantic_candidate_keys=["document_chunk_0"],
    )
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(step_id="semantic_search_1", title="Search", goal="Find chunk", tool="memory_semantic_search"),
            PlanStep(
                step_id="workspace_2",
                title="Read chunk",
                goal="Read chunk",
                tool="workspace_get",
                tool_arguments={"entry_id": 2, "document_source_step": "semantic_search_1"},
            ),
            PlanStep(
                step_id="workspace_1",
                title="Read overview",
                goal="Read overview",
                tool="workspace_get",
                tool_arguments={"entry_id": 1},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="verify-plan-3",
    )

    result = build_verifier_input("Was passiert in PREGO!?", plan, document_context=document)

    retrieval_plan = result.document_meta["retrieval_plan"]
    assert retrieval_plan["search_step_ids"] == ["semantic_search_1"]
    assert retrieval_plan["search_driven_workspace_reads"] == [
        {"step_id": "workspace_2", "entry_id": 2, "source_step": "semantic_search_1"}
    ]
    assert retrieval_plan["direct_workspace_reads"] == [{"step_id": "workspace_1", "entry_id": 1}]
