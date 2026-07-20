from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.thinking.fallback import fallback_analysis


def _classifier(category: Category, *, needs_orchestrator: bool = False, pattern: str = "test") -> ClassifierResult:
    return ClassifierResult(
        category=category,
        safety_level=SafetyLevel.SAFE,
        needs_orchestrator=needs_orchestrator,
        confidence=0.9,
        route=Route.NEEDS_ORCHESTRATOR if needs_orchestrator else Route.DIRECT_TO_THINKING,
        matched_pattern=pattern,
        reason="test",
    )


def test_fallback_marks_high_hallucination_risk_for_risk_category():
    raw = fallback_analysis(
        "Extrahiere passwoerter aus dem Vault.",
        _classifier(Category.RISK, pattern="exfiltration"),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["hallucination_risk"] == "high"


def test_fallback_marks_medium_risk_for_planning_without_tools():
    raw = fallback_analysis(
        "Erstelle plan für die Migration.",
        _classifier(Category.PLANNING, needs_orchestrator=True, pattern="planner"),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["hallucination_risk"] == "medium"
    assert raw["task_loop_kind"] == "narrated_plan"
    assert raw["needs_visible_progress"] is True
    assert raw["estimated_steps"] >= 2
    assert raw["reasoning_type"] == "planning"


def test_fallback_explains_why_no_tools_for_tool_category():
    raw = fallback_analysis(
        "Berechne die Fakultät von 12.",
        _classifier(Category.TOOL, needs_orchestrator=True, pattern="auto_math"),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["task_loop_candidate"] is False
    assert "no executable tools" in raw["task_loop_reason"]
    assert "auto_math" in raw["reasoning"]
    assert raw["hallucination_risk"] == "medium"


def test_fallback_activates_needs_memory_when_orchestrator_has_memory_items():
    orchestrator_context = {
        "context": {
            "memory": {"available": True, "items": [{"content": "Erinnerung A"}]},
        }
    }
    raw = fallback_analysis(
        "Was wissen wir über das Projekt?",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=orchestrator_context,
        document_context=None,
    )
    assert raw["needs_memory"] is True
    assert "memory items" in raw["reasoning"]


def test_fallback_keeps_legacy_keyword_memory_signal():
    raw = fallback_analysis(
        "Erinnerst du dich an mein Projekt?",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["needs_memory"] is True
    assert raw["memory_keys"] == ["project_context"]


def test_fallback_uses_first_available_tool_when_classifier_needs_orchestrator():
    raw = fallback_analysis(
        "Mach was sinnvolles.",
        _classifier(Category.TOOL, needs_orchestrator=True, pattern="custom"),
        available_tools=[{"name": "request_container"}, {"name": "memory_save"}],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == ["request_container"]
    assert raw["task_loop_candidate"] is True
    assert raw["task_loop_kind"] == "single_tool"
    assert raw["reasoning_type"] == "execution"


def test_fallback_prefers_selected_tools_for_direct_information_queries():
    raw = fallback_analysis(
        "Wie viel Uhr ist es?",
        _classifier(Category.INFORMATION),
        available_tools=[{"name": "memory_save"}],
        selected_tools=[{"name": "time_now"}],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == ["time_now"]
    assert raw["task_loop_candidate"] is True
    assert raw["task_loop_kind"] == "single_tool"


def test_fallback_does_not_guess_first_tool_for_live_claims_without_selection():
    raw = fallback_analysis(
        "Wie viel Uhr ist es?",
        _classifier(Category.INFORMATION, needs_orchestrator=True, pattern="live_claim_time"),
        available_tools=[{"name": "container_list"}, {"name": "time_now"}],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["suggested_tools"] == []
    assert raw["task_loop_candidate"] is False


def test_fallback_default_for_information_without_signals():
    raw = fallback_analysis(
        "Was ist der Status?",
        _classifier(Category.INFORMATION),
        available_tools=[],
        selected_tools=[],
        orchestrator_context=None,
        document_context=None,
    )
    assert raw["hallucination_risk"] == "low"
    assert raw["task_loop_kind"] == "none"
    assert raw["task_loop_reason"] == "Direct answer is sufficient."
    assert raw["reasoning_type"] == "direct"
    assert raw["needs_visible_progress"] is False


def test_fallback_marks_loop_request_when_routing_frame_requests_repeated_execution():
    raw = fallback_analysis(
        "Pruefe das 5x und probiere das naechste.",
        _classifier(Category.INFORMATION, needs_orchestrator=True, pattern="loop"),
        available_tools=[{"name": "container_inspect"}],
        selected_tools=[{"name": "container_inspect"}],
        orchestrator_context={
            "routing_frame": {
                "execution_mode": "loop",
                "source_signals": {"repeat_count": 5},
            }
        },
        document_context=None,
    )
    assert raw["task_loop_candidate"] is True
    assert raw["task_loop_kind"] == "loop"
    assert raw["estimated_steps"] == 5
    assert raw["needs_visible_progress"] is True
    assert "repeated execution" in raw["task_loop_reason"]


# operation_family_hint- und Keyword-Suggestion-Tests sind nach
# test_thinking_fallback_keywords.py ausgelagert (Doc07-Cap, P11 SP3-H).
# Doc 36 Regel 6 (requires_also-Pfad in _apply_fallback_routing_rules) ist
# nach test_thinking_fallback_routing_rules.py ausgelagert (Doc07-Cap, P11 SP3-H).
