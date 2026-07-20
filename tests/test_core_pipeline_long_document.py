import asyncio

from core.output.contracts import OutputResult
from core.pipeline import runner
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from tests._core_pipeline_request_helpers import core_pipeline_request
from tests._eligible_tool_fixtures import eligible_raw_tool


def test_core_long_document_path_uses_document_summary_for_thinking(monkeypatch):
    seen = {}

    def classify_long(user_text):
        from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel

        return ClassifierResult(
            category=Category.INFORMATION,
            safety_level=SafetyLevel.SAFE,
            needs_orchestrator=False,
            confidence=1.0,
            route=Route.DIRECT_TO_THINKING,
            matched_pattern="long_document",
            reason="detected large document",
            is_long_document=True,
            estimated_input_tokens=9000,
        )

    def build_doc_plan(user_text, classifier_result, **kwargs):
        seen["planning_user_text"] = user_text
        seen["thinking_context"] = kwargs.get("orchestrator_context")
        return ThinkingPlan(
            intent="review_document",
            steps=[PlanStep(step_id="answer_user", title="Antwort", goal="Antwort geben", risk=RiskLevel.SAFE)],
            needs_task_loop=False,
            risk_level=RiskLevel.SAFE,
            reasoning="summary-based planning",
            context_hints={},
            plan_id="doc-plan-1",
        )

    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        seen["output_user_text"] = output_request.user_text
        return OutputResult(content="document answer")

    def save_workspace(conversation_id, content, entry_type, source_layer):
        seen.setdefault("workspace", []).append((conversation_id, entry_type, source_layer))
        return 100 + len(seen["workspace"])

    def save_semantic(conversation_id, content, content_type, key, value):
        seen.setdefault("semantic", []).append((conversation_id, content_type, key, value))
        return {"success": True}

    monkeypatch.setattr(runner, "classify", classify_long)
    monkeypatch.setattr(runner, "build_plan", build_doc_plan)

    long_text = "Titel\n\n" + ("Absatz mit viel Inhalt. " * 400) + "\n\nFazit des Dokuments."
    response = asyncio.run(
        runner.run_chat(
            core_pipeline_request(long_text),
            output_fn=fake_output,
            orchestrator_raw_tools=[
                eligible_raw_tool("workspace_get", "Read workspace entry", "sql-memory"),
                eligible_raw_tool("memory_semantic_search", "Search memory", "sql-memory"),
            ],
            document_workspace_save_fn=save_workspace,
            document_semantic_save_fn=save_semantic,
        )
    )

    assert response.content == "document answer"
    assert seen["planning_user_text"].startswith("Dokumentzusammenfassung fuer Planning:")
    assert seen["output_user_text"] == long_text
    assert seen["output_context"]["document"]["original_char_count"] == len(long_text)
    assert seen["output_context"]["document"]["total_chunks"] >= 1
    assert seen["thinking_context"]["selected_tools"] == ["memory_semantic_search", "workspace_get"]
    assert seen["output_context"]["document_tools"]["selected_tools"] == ["memory_semantic_search", "workspace_get"]
    assert seen["output_context"]["document_tools"]["tool_mode"] == "semantic_first"
    assert seen["output_context"]["document"]["workspace_entry_ids"]
    assert seen["output_context"]["document"]["semantic_keys"]
    assert seen["workspace"][0] == ("p0-test", "document_chunk", "input_processor")
    assert seen["semantic"][0][1] == "document_chunk"


def test_core_long_document_passes_document_context_into_verifier(monkeypatch):
    seen = {}

    def classify_long(user_text):
        from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel

        return ClassifierResult(
            category=Category.INFORMATION,
            safety_level=SafetyLevel.SAFE,
            needs_orchestrator=False,
            confidence=1.0,
            route=Route.DIRECT_TO_THINKING,
            matched_pattern="long_document",
            reason="detected large document",
            is_long_document=True,
            estimated_input_tokens=9000,
        )

    def fake_build_plan(user_text, classifier_result, **kwargs):
        return ThinkingPlan(
            intent="inspect_document",
            steps=[PlanStep(step_id="answer_user", title="Antwort", goal="Antwort geben", risk=RiskLevel.SAFE)],
            needs_task_loop=False,
            risk_level=RiskLevel.SAFE,
            reasoning="ok",
            context_hints={},
            plan_id="verify-doc-plan",
        )

    def fake_verify(plan, user_text="", **kwargs):
        seen["user_text"] = user_text
        seen["document_context"] = kwargs.get("document_context")
        return VerifierResult(verdict=Verdict.APPROVED, reason="ok")

    async def fake_output(output_request, chat_request):
        return OutputResult(content="ok")

    monkeypatch.setattr(runner, "classify", classify_long)
    monkeypatch.setattr(runner, "build_plan", fake_build_plan)
    monkeypatch.setattr(runner, "verify_plan", fake_verify)

    long_text = "Titel\n\n" + ("Absatz mit viel Inhalt. " * 400) + "\n\nFazit des Dokuments."
    response = asyncio.run(runner.run_chat(core_pipeline_request(long_text), output_fn=fake_output))

    assert response.content == "ok"
    assert seen["user_text"] == long_text
    assert seen["document_context"] is not None
    assert seen["document_context"].summary.startswith("Dokumentzusammenfassung fuer Planning:")
