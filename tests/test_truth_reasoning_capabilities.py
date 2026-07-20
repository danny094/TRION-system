from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.task_loop.executor import TaskToolCall, TaskToolResult
from core.task_loop.task_loop import start_task_loop
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


def test_analyzer_resolves_file_capability_from_live_tool_details():
    raw = analyze_request(
        "Lies danach /trion-home/status.txt.",
        _classifier(),
        available_tools=[
            {
                "name": "workspace_get",
                "description": "Read a workspace entry by id.",
                "intent_description": "Read file or document content from the workspace.",
                "intent_keywords": ["file", "read", "workspace", "document"],
            }
        ],
        selected_tools=[],
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == ["workspace_get"]
    assert raw["additional_evidence_needed"] == {}


def test_task_loop_replans_for_additional_evidence_using_regular_second_step():
    plan = build_plan_from_analysis(
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
    )
    calls: list[str] = []

    def tool_runner(call: TaskToolCall) -> TaskToolResult:
        calls.append(call.tool_name)
        if call.tool_name == "time_now":
            return TaskToolResult(success=True, result={"utc_iso": "2026-05-24T18:41:23Z"})
        if call.tool_name == "workspace_get":
            return TaskToolResult(success=True, result={"value": "Systemstatus: OK"})
        return TaskToolResult(success=False, error="unexpected_tool")

    result = start_task_loop(
        plan,
        conversation_id="truth-reasoning",
        objective="Prüfe zuerst die aktuelle Uhrzeit. Lies danach /trion-home/status.txt.",
        tool_runner=tool_runner,
        replanner_fn=lambda *args, **kwargs: build_replan(*args, **kwargs, available_tools=["time_now", "workspace_get"]),
    )

    assert result.state.value == "completed"
    assert calls == ["time_now", "workspace_get"]
