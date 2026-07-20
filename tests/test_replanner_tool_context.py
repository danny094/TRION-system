from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus, TaskLoopSnapshot, TaskLoopState
from core.thinking.planner import build_plan_from_analysis
from core.thinking.replanner import build_replan

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _plan(suggested_tools=None):
    return build_plan_from_analysis(
        {"intent": "Deploy app", "suggested_tools": suggested_tools or ["old_tool"]},
        user_text="Deploy app",
    )


def _snapshot():
    return TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="Deploy app",
        state=TaskLoopState.REPLANNING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        max_replans=2,
    )


def _failure():
    return StepExecutionResult(step_id="step_1", status=StepExecutionStatus.FAILED, error="timeout")


def _capturing_analyzer(captured: dict):
    def _fake(user_text, classifier_result, **kwargs):
        captured.update(kwargs)
        return {"intent": "retry", "suggested_tools": []}
    return _fake


def test_build_replan_falls_back_to_plan_suggested_tools_when_none(monkeypatch):
    captured = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", _capturing_analyzer(captured))

    build_replan(
        _plan(suggested_tools=["old_tool"]),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
        available_tools=None,
    )

    assert captured["available_tools"] == ["old_tool"]


def test_build_replan_passes_fresh_available_tools_to_analyzer(monkeypatch):
    captured = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", _capturing_analyzer(captured))

    fresh_tools = [{"name": "new_tool", "description": "Fresh from MCP hub"}]
    build_replan(
        _plan(suggested_tools=["old_tool"]),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
        available_tools=fresh_tools,
    )

    assert captured["available_tools"] == fresh_tools


def test_build_replan_empty_list_is_not_treated_as_none(monkeypatch):
    """available_tools=[] is a valid empty override — must not fall back to plan.suggested_tools."""
    captured = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", _capturing_analyzer(captured))

    build_replan(
        _plan(suggested_tools=["old_tool"]),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
        available_tools=[],
    )

    assert captured["available_tools"] == []


def test_build_replan_passes_orchestrator_context_to_analyzer(monkeypatch):
    captured = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", _capturing_analyzer(captured))

    ctx = {"conversation_policy": {"memory_mode": "global_enabled"}}
    build_replan(
        _plan(),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
        orchestrator_context=ctx,
    )

    assert captured["orchestrator_context"] == ctx


def test_build_replan_orchestrator_context_defaults_to_none(monkeypatch):
    captured = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", _capturing_analyzer(captured))

    build_replan(
        _plan(),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
    )

    assert captured.get("orchestrator_context") is None


def test_build_replan_replan_hint_captures_failure_details(monkeypatch):
    monkeypatch.setattr(
        "core.thinking.replanner.analyze_request",
        lambda *a, **kw: {"intent": "retry", "suggested_tools": []},
    )

    result = build_replan(
        _plan(),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
    )

    hint = result.context_hints["replan"]
    assert hint["failed_step_id"] == "step_1"
    assert hint["error"] == "timeout"
    assert hint["replan_count"] == 0


# ---------------------------------------------------------------------------
# Phase 4: orchestrator_context wird an build_plan_from_analysis weitergegeben
# ---------------------------------------------------------------------------


def _capturing_planner(captured: dict):
    def _fake(raw_plan, *, user_text, classifier_result=None, orchestrator_context=None, **kw):
        captured["orchestrator_context"] = orchestrator_context
        return build_plan_from_analysis(
            raw_plan,
            user_text=user_text,
            classifier_result=classifier_result,
        )
    return _fake


def test_build_replan_passes_orchestrator_context_to_planner(monkeypatch):
    """orchestrator_context muss an build_plan_from_analysis weitergegeben werden."""
    captured: dict = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", lambda *a, **kw: {"intent": "retry", "suggested_tools": []})
    monkeypatch.setattr("core.thinking.replanner.build_plan_from_analysis", _capturing_planner(captured))

    ctx = {"active_containers": [{"id": "abc123"}]}
    build_replan(
        _plan(),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
        orchestrator_context=ctx,
    )

    assert captured["orchestrator_context"] == ctx


def test_build_replan_planner_gets_none_context_when_not_provided(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("core.thinking.replanner.analyze_request", lambda *a, **kw: {"intent": "retry", "suggested_tools": []})
    monkeypatch.setattr("core.thinking.replanner.build_plan_from_analysis", _capturing_planner(captured))

    build_replan(
        _plan(),
        objective="Deploy app",
        failed_step_id="step_1",
        failure=_failure(),
        snapshot=_snapshot(),
    )

    assert captured["orchestrator_context"] is None
