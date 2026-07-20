import asyncio

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.thinking.analyzer import analyze_request
from core.thinking.planner import build_plan_from_analysis
from core.thinking.replanner import build_replan


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=True,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR,
        matched_pattern="live_claim_time",
        reason="test",
    )


def _chat_request(text: str) -> CoreChatRequest:
    return CoreChatRequest(
        model="default",
        messages=[Message(role=MessageRole.USER, content=text)],
        conversation_id="truth-reasoning",
    )


def test_analyzer_detects_time_projection_and_derivation():
    raw = analyze_request(
        "Wie viel Uhr ist es gerade? Und in einer Stunde nur als UTC ISO ausgeben.",
        _classifier(),
        available_tools=["time_now"],
        selected_tools=["time_now"],
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["time_now"]
    assert raw["response_projection"] == "utc_iso"
    assert raw["response_derivation"] == {"kind": "time_offset", "seconds": 3600}


def test_planner_carries_additional_evidence_need_forward():
    plan = build_plan_from_analysis(
        {
            "intent": "Pruefe Uhrzeit und Datei",
            "suggested_tools": ["time_now"],
            "additional_evidence_needed": {
                "kind": "file_read",
                "reason": "The request also asks for verified file content, but no file-read tool is selected.",
                "candidate_tools": [],
            },
        },
        user_text="Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt.",
        classifier_result=_classifier(),
    )

    assert plan.additional_evidence_need is not None
    assert plan.additional_evidence_need.kind == "file_read"
    assert "file content" in plan.additional_evidence_need.reason


def test_replan_prefers_only_missing_additional_tool_after_grounded_time():
    replanned = build_replan(
        build_plan_from_analysis(
                {
                    "intent": "Pruefe Uhrzeit und Datei",
                    "suggested_tools": ["time_now"],
                    "additional_evidence_needed": {
                        "kind": "file_read",
                        "reason": "The request also asks for verified file content, but no file-read tool is selected.",
                        "candidate_tools": ["workspace_get"],
                    },
            },
            user_text="Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt.",
            classifier_result=_classifier(),
        ),
        objective="Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt.",
        failed_step_id="tool_1",
        failure=None,
        snapshot=type("Snapshot", (), {"replan_count": 0, "artifacts": [{"artifact_type": "tool_result", "tool": "time_now"}]})(),
        available_tools=["time_now", "workspace_get"],
    )

    assert replanned.suggested_tools == ["workspace_get"]
    assert replanned.additional_evidence_need is None


def test_generate_output_projects_time_to_utc_iso_from_grounded_result():
    plan = build_plan_from_analysis(
        {
            "intent": "Zeit als UTC ISO",
            "suggested_tools": ["time_now"],
            "response_projection": "utc_iso",
        },
        user_text="Wie viel Uhr ist es gerade? Und gib die Antwort danach nur als UTC ISO aus.",
        classifier_result=_classifier(),
    )

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel Uhr ist es gerade? Und gib die Antwort danach nur als UTC ISO aus.",
                thinking_plan=plan,
                context={
                    "grounded_tool_results": [
                        {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-24T18:41:23Z"}}
                    ]
                },
            ),
            _chat_request("Wie viel Uhr ist es gerade? Und gib die Antwort danach nur als UTC ISO aus."),
        )
    )

    assert result.content == "2026-05-24T18:41:23Z"


def test_generate_output_refuses_partial_answer_when_additional_evidence_is_missing():
    plan = build_plan_from_analysis(
        {
            "intent": "Pruefe Uhrzeit und Datei",
            "suggested_tools": ["time_now"],
            "additional_evidence_needed": {
                "kind": "file_read",
                "reason": "The request also asks for verified file content, but no file-read tool is selected.",
                "candidate_tools": [],
            },
        },
        user_text="Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt.",
        classifier_result=_classifier(),
    )

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt.",
                thinking_plan=plan,
                context={
                    "grounded_tool_results": [
                        {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-24T18:41:23Z"}}
                    ]
                },
            ),
            _chat_request("Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt."),
        )
    )

    assert "kein verfügbares Tool" in result.content
    assert "/trion-home/status.txt" in result.content
