from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.thinking.analyzer import analyze_request


def _classifier() -> ClassifierResult:
    return ClassifierResult(
        category=Category.INFORMATION,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=False,
        confidence=0.9,
        route=Route.DIRECT_TO_THINKING,
        matched_pattern="test",
        reason="test",
    )


def test_analyzer_keeps_orchestrator_selected_tools_when_llm_omits_them():
    async def fake_complete_prompt(**kwargs):
        return '{"intent":"answer_user","reasoning":"Need a precise answer."}'

    raw = analyze_request(
        "Wie viel Uhr ist es?",
        _classifier(),
        selected_tools=["time_now"],
        complete_prompt_fn=fake_complete_prompt,
        llm_enabled=True,
    )

    assert raw["suggested_tools"] == ["time_now"]
    assert raw["task_loop_candidate"] is True
    assert raw["task_loop_kind"] == "single_tool"
    assert "Orchestrator selected executable tool candidates." in raw["reasoning"]


def test_analyzer_preserves_explicit_llm_tool_selection():
    async def fake_complete_prompt(**kwargs):
        return '{"intent":"answer_user","suggested_tools":["time_now"],"reasoning":"Use time tool.","needs_loop":false,"repeat_count_hint":1}'

    raw = analyze_request(
        "Wie viel Uhr ist es?",
        _classifier(),
        selected_tools=["time_now"],
        complete_prompt_fn=fake_complete_prompt,
        llm_enabled=True,
    )

    assert raw["suggested_tools"] == ["time_now"]
    assert raw["reasoning"] == "Use time tool."
    assert raw["needs_loop"] is False
    assert raw["repeat_count_hint"] == 1


def test_analyzer_normalizes_natural_language_loop_hint_from_llm():
    async def fake_complete_prompt(**kwargs):
        return '{"intent":"Führe 3 Suchen aus","suggested_tools":["memory_graph_search"],"needs_loop":true,"repeat_count_hint":3,"operation_family_hint":"search","reasoning":"User requested repeated memory searches."}'

    raw = analyze_request(
        'Führe 3 Memory-Suchen aus: "Python", "Projekt", "Name".',
        _classifier(),
        selected_tools=["memory_graph_search"],
        complete_prompt_fn=fake_complete_prompt,
        llm_enabled=True,
    )

    assert raw["suggested_tools"] == ["memory_graph_search"]
    assert raw["needs_loop"] is True
    assert raw["repeat_count_hint"] == 3
    assert raw["task_loop_kind"] == "loop"


def test_analyzer_suppresses_selected_time_tool_for_derivable_followup():
    raw = analyze_request(
        "Und in einer Stunde?",
        _classifier(),
        selected_tools=["time_now"],
        orchestrator_context={
            "grounding_state": {
                "grounded_results": [
                    {
                        "tool_name": "time_now",
                        "facts": {"utc_iso": "2026-05-12T03:26:51Z"},
                    }
                ]
            }
        },
        llm_enabled=False,
    )

    assert raw["suggested_tools"] == []
    assert raw["task_loop_candidate"] is False
    assert raw["task_loop_kind"] == "none"
    assert "Existing grounded time evidence is sufficient" in raw["reasoning"]
