import asyncio
import re

from core.output.contracts import OutputResult
from core.pipeline import runner
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from tests._eligible_tool_fixtures import eligible_raw_tool
from tests.test_documententest_support import enable_documententest_chunking, fixture_text, request_from_fixture



def test_documententest_fixture_contains_eleven_toc_entries():
    text = fixture_text()
    toc_start = text.index("Inhaltsverzeichnis")
    toc_end = text.index("\n2\nPREGO!")
    toc_block = text[toc_start:toc_end]
    entries = re.findall(r"^(?!Inhaltsverzeichnis)(.+?)\.{3,}\d+$", toc_block, flags=re.MULTILINE)
    assert len(entries) == 11


def test_documententest_story_activates_document_pipeline(monkeypatch):
    seen = {}

    def fake_build_plan(user_text, classifier_result, **kwargs):
        seen["planning_user_text"] = user_text
        seen["classifier_result"] = classifier_result
        seen["thinking_context"] = kwargs.get("orchestrator_context")
        seen["document_context"] = kwargs.get("document_context")
        return ThinkingPlan(
            intent="inspect_document",
            steps=[PlanStep(step_id="answer_user", title="Antwort", goal="Antwort geben", risk=RiskLevel.SAFE)],
            needs_task_loop=False,
            risk_level=RiskLevel.SAFE,
            reasoning="document test",
            context_hints={},
            plan_id="documententest-plan",
        )

    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        return OutputResult(content="ok")

    def save_workspace(conversation_id, content, entry_type, source_layer):
        seen.setdefault("workspace", []).append((conversation_id, entry_type, source_layer))
        return 200 + len(seen["workspace"])

    def save_semantic(conversation_id, content, content_type, key, value):
        seen.setdefault("semantic", []).append((conversation_id, content_type, key, value))
        return {"success": True}

    enable_documententest_chunking(monkeypatch)
    monkeypatch.setattr(runner, "build_plan", fake_build_plan)
    monkeypatch.setattr(runner, "verify_plan", lambda *a, **kw: VerifierResult(verdict=Verdict.APPROVED, reason="test_bypass"))

    response = asyncio.run(
        runner.run_chat(
            request_from_fixture(),
            output_fn=fake_output,
            orchestrator_raw_tools=[
                eligible_raw_tool("workspace_get", "Read workspace entry", "sql-memory"),
                eligible_raw_tool("memory_semantic_search", "Search memory", "sql-memory"),
            ],
            document_workspace_save_fn=save_workspace,
            document_semantic_save_fn=save_semantic,
        )
    )

    assert response.content == "ok"
    assert seen["classifier_result"].is_long_document is True
    assert seen["planning_user_text"].startswith("Dokumentzusammenfassung fuer Planning:")
    assert seen["document_context"].total_chunks > 1
    assert seen["thinking_context"]["selected_tools"] == ["workspace_get", "memory_semantic_search"]
    assert seen["output_context"]["document_tools"]["tool_mode"] == "structure_first"
    assert len(seen["output_context"]["document"]["workspace_entry_ids"]) > 0
    assert len(seen["output_context"]["document"]["preferred_entry_ids"]) > 0
    assert len(seen["output_context"]["document"]["semantic_keys"]) > 0
