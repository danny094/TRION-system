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
