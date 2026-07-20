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
        user_text='Führe 3 Memory-Suchen aus: "Python", "Projekt", "Name".',
        classifier_result=_classifier(True),
        orchestrator_context={
            "selected_tools": ["memory_graph_search"],
            "selected_tool_details": [{"name": "memory_graph_search", "capability_required_args": ["query"]}],
            "context": {"routing_frame": {"execution_mode": "retrieve_context"}},
        },
    )

    assert plan.intent == "3 Memory-Suchen ausführen"
    assert plan.suggested_tools == ["memory_graph_search"]
    assert plan.needs_task_loop is True
    assert [step.tool for step in plan.steps] == ["memory_graph_search", "memory_graph_search", "memory_graph_search"]
    assert [step.tool_arguments["query"] for step in plan.steps] == ["Python", "Projekt", "Name"]


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


def test_analyzer_preserves_preselected_document_tool_order():
    document = process_long_input(
        "Inhaltsverzeichnis\nPREGO! ..... 3\n\nPREGO!\nCarolin hilft Ameisen.",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 11,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=20,
        overlap_tokens=5,
    )

    raw = analyze_request(
        "Was passiert in PREGO!?",
        _classifier(False),
        selected_tools=["memory_semantic_search", "workspace_get"],
        document_context=document,
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["memory_semantic_search", "workspace_get"]
    assert raw["document_retrieval_mode"] == "semantic_first"


def test_analyzer_preserves_document_tool_mode_from_context():
    document = process_long_input(
        "Inhaltsverzeichnis\nPREGO! ..... 3\n\nPREGO!\nCarolin hilft Ameisen.",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 11,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=20,
        overlap_tokens=5,
    )

    raw = analyze_request(
        "Wie viele Kapitel hat diese Geschichte?",
        _classifier(False),
        selected_tools=["workspace_get", "memory_semantic_search"],
        orchestrator_context={"document_tool_mode": "structure_first"},
        document_context=document,
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["workspace_get", "memory_semantic_search"]
    assert raw["document_retrieval_mode"] == "structure_first"


def test_analyzer_maps_single_document_tool_to_workspace_only_mode():
    document = process_long_input(
        "Inhaltsverzeichnis\nPREGO! ..... 3\n\nPREGO!\nCarolin hilft Ameisen.",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 11,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=20,
        overlap_tokens=5,
    )

    raw = analyze_request(
        "Was steht in dem Dokument?",
        _classifier(False),
        selected_tools=["workspace_get"],
        document_context=document,
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["workspace_get"]
    assert raw["document_retrieval_mode"] == "workspace_only"


def test_analyzer_maps_exact_question_with_single_workspace_tool_to_exact_lookup():
    document = process_long_input(
        "Inhaltsverzeichnis\nPREGO! ..... 3\n\nPREGO!\nCarolin hilft Ameisen.",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 11,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=20,
        overlap_tokens=5,
    )

    raw = analyze_request(
        "Wo steht das genau?",
        _classifier(False),
        selected_tools=["workspace_get"],
        document_context=document,
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["workspace_get"]
    assert raw["document_retrieval_mode"] == "exact_lookup"


def test_analyzer_maps_structure_question_with_mixed_tools_to_structure_first():
    document = process_long_input(
        "Inhaltsverzeichnis\nPREGO! ..... 3\nKapitel 2 ..... 7\n\nPREGO!\nCarolin hilft Ameisen.",
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 11,
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=20,
        overlap_tokens=5,
    )

    raw = analyze_request(
        "Wie viele Kapitel hat diese Geschichte?",
        _classifier(False),
        selected_tools=["workspace_get", "memory_semantic_search"],
        document_context=document,
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["workspace_get", "memory_semantic_search"]
    assert raw["document_retrieval_mode"] == "structure_first"


def test_reduce_orchestrator_context_keeps_policy_and_truncates_lists():
    summary = reduce_orchestrator_context(
        {
            "conversation_policy": {
                "memory_mode": "conversation_only",
                "allow_global_memory_read": False,
                "allow_long_term_write": False,
                "allowed_namespaces": ["workspace"],
            },
            "workspace": {
                "available": True,
                "items": [
                    {"id": "1", "title": "alpha"},
                    {"id": "2", "title": "beta"},
                    {"id": "3", "title": "gamma"},
                    {"id": "4", "title": "delta"},
                ],
            },
        },
        item_cap=2,
        char_cap=600,
    )

    assert '"memory_mode": "conversation_only"' in summary
    assert '"count": 4' in summary
    assert '"title": "alpha"' in summary
    assert '"title": "beta"' in summary
    assert '"title": "gamma"' not in summary


def test_build_thinking_prompt_includes_reduced_context_block():
    prompt = build_thinking_prompt(
        "Starte den Container",
        available_tools=["request_container"],
        context_summary='{"conversation_policy":{"memory_mode":"conversation_only"}}',
    )

    assert "VERFUEGBARE TOOLS" not in prompt
    assert "VERFÜGBARE TOOLS" in prompt
    assert "REDUZIERTER ORCHESTRATOR-KONTEXT" in prompt
    assert '"memory_mode":"conversation_only"' in prompt


def test_build_thinking_prompt_includes_document_context_block():
    document = process_long_input(
        "Einleitung\n\n" + ("Langtext " * 40) + "\n\nSchluss",
        conversation_id="conv-1",
        max_tokens=20,
        overlap_tokens=5,
    )
    prompt = build_thinking_prompt(
        "Dokument pruefen",
        document_context_summary=reduce_document_context(document),
    )

    assert "DOKUMENT-KONTEXT" in prompt
    assert '"workspace_entry_ids"' in prompt
    assert '"total_chunks": 3' in prompt


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


def test_input_processor_detects_and_summarizes_long_document(monkeypatch):
    monkeypatch.setattr("core.input_processor.detect.ENABLE_CHUNKING", True)
    monkeypatch.setattr("core.input_processor.detect.CHUNKING_THRESHOLD", 10)

    text = "Einleitung\n\n" + ("Langtext " * 40) + "\n\nSchluss"
    assert estimate_input_tokens(text) >= 10
    assert is_long_document(text) is True

    document = process_long_input(text, max_tokens=20, overlap_tokens=5)

    assert document.original_char_count == len(text)
    assert document.total_chunks == 3
    assert document.summary.startswith("Dokumentzusammenfassung fuer Planning:")
    assert document.key_facts
    assert document.semantic_keys == []
    assert document.preferred_entry_ids == []
    assert document.index_like_entry_ids == []
    assert document.chapter_candidate_entry_ids == []
    assert document.semantic_candidate_keys == []


def test_input_processor_chunks_and_stores_with_injected_hooks():
    seen = {"workspace": [], "semantic": []}

    def save_workspace(conversation_id, content, entry_type, source_layer):
        seen["workspace"].append((conversation_id, content, entry_type, source_layer))
        return len(seen["workspace"])

    def save_semantic(conversation_id, content, content_type, key, value):
        seen["semantic"].append((conversation_id, content, content_type, key, value))
        return {"success": True}

    text = " ".join(f"token{i}" for i in range(12))
    chunks = chunk_document(text, max_tokens=5, overlap_tokens=1)
    document = process_long_input(
        text,
        conversation_id="conv-1",
        workspace_save_fn=save_workspace,
        semantic_save_fn=save_semantic,
        max_tokens=5,
        overlap_tokens=1,
    )

    assert len(chunks) == 3
    assert document.total_chunks == 3
    assert document.workspace_entry_ids == [1, 2, 3]
    assert document.preferred_entry_ids == [1, 2, 3]
    assert document.semantic_keys == ["document_chunk_0", "document_chunk_1", "document_chunk_2"]
    assert document.semantic_candidate_keys == ["document_chunk_0", "document_chunk_1", "document_chunk_2"]
    assert seen["workspace"][0][0] == "conv-1"
    assert seen["workspace"][0][2] == "document_chunk"
    assert seen["semantic"][0][3] == "document_chunk_0"


def test_tools_json_includes_capability_evidence_types():
    """T9: dict-Tool mit capability_evidence_types → erscheint im JSON-Output von _tools_json."""
    from core.thinking.prompts import _tools_json
    tools = [
        {
            "name": "container_inspect",
            "description": "Inspect a container",
            "mcp": "container-commander",
            "capability_evidence_types": ["thermal_scan"],
        }
    ]
    result = _tools_json(tools)
    assert '"capability_evidence_types"' in result
    assert '"thermal_scan"' in result


def test_tools_json_omits_capability_evidence_types_when_empty():
    """T10: Tool ohne capability_evidence_types → Schlüssel fehlt im JSON-Output (Backward-compat)."""
    from core.thinking.prompts import _tools_json
    tools = [{"name": "memory_save", "description": "Save memory", "mcp": "sql-memory"}]
    result = _tools_json(tools)
    assert "capability_evidence_types" not in result


def test_tools_json_handles_plain_string_tool_names():
    """T10b: String-Fallback — plain Tool-Namen wie ['container_inspect'] → name korrekt, kein leeres dict."""
    from core.thinking.prompts import _tools_json
    import json
    result = _tools_json(["container_inspect", "memory_save"])
    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0]["name"] == "container_inspect"
    assert parsed[1]["name"] == "memory_save"
    # description/mcp leer aber vorhanden — kein getattr-Artefakt
    assert parsed[0].get("description", "") == ""


def test_input_processor_detects_index_like_and_chapter_candidate_chunks():
    text = (
        "Inhaltsverzeichnis\n"
        "Kapitel 1 ..... 1\n"
        "Kapitel 2 ..... 5\n"
        "Kapitel 3 ..... 8\n\n"
        "Kapitel 1 Der Anfang\nText Text Text\n\n"
        "Kapitel 2 Die Reise\nMehr Text"
    )

    document = process_long_input(
        text,
        conversation_id="conv-1",
        workspace_save_fn=lambda *_: 10 + len(text),
        semantic_save_fn=lambda *_: {"success": True},
        max_tokens=40,
        overlap_tokens=5,
    )

    assert document.index_like_entry_ids
    assert document.chapter_candidate_entry_ids
    assert document.preferred_entry_ids == document.index_like_entry_ids[:4]
