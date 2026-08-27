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
