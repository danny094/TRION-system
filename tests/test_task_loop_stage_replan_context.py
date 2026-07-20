from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.task_loop_stage import _bind_replan_context
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import ThinkingPlan, RiskLevel


def _record(*args, **kwargs):
    return {"args": args, "kwargs": kwargs}


def test_bind_is_noop_when_both_none():
    bound = _bind_replan_context(_record, None, None)
    assert bound is _record


def test_bind_injects_available_tools():
    tools = [{"name": "tool_a"}]
    bound = _bind_replan_context(_record, tools, None)
    result = bound("plan", objective="obj")
    assert result["kwargs"]["available_tools"] == tools


def test_bind_injects_orchestrator_context():
    ctx = {"system": "state"}
    bound = _bind_replan_context(_record, None, ctx)
    result = bound("plan", objective="obj")
    assert result["kwargs"]["orchestrator_context"] == ctx


def test_bind_injects_both_tools_and_context():
    tools = [{"name": "t"}]
    ctx = {"k": "v"}
    bound = _bind_replan_context(_record, tools, ctx)
    result = bound("plan", objective="obj")
    assert result["kwargs"]["available_tools"] == tools
    assert result["kwargs"]["orchestrator_context"] == ctx


def test_bind_does_not_override_explicit_available_tools():
    """setdefault must not replace a value the caller provides explicitly."""
    bound = _bind_replan_context(_record, [{"name": "default_tool"}], None)
    explicit = [{"name": "explicit_tool"}]
    result = bound("plan", available_tools=explicit)
    assert result["kwargs"]["available_tools"] == explicit


def test_bind_does_not_override_explicit_orchestrator_context():
    bound = _bind_replan_context(_record, None, {"default": True})
    explicit_ctx = {"explicit": True}
    result = bound("plan", orchestrator_context=explicit_ctx)
    assert result["kwargs"]["orchestrator_context"] == explicit_ctx


def test_bind_preserves_positional_args():
    tools = [{"name": "t"}]
    bound = _bind_replan_context(_record, tools, None)
    result = bound("plan_arg", "second_arg", objective="test")
    assert result["args"] == ("plan_arg", "second_arg")


def test_bind_wraps_even_for_empty_available_tools():
    """Empty list is a valid override (all tools blocked) — wrapper must be created."""
    bound = _bind_replan_context(_record, [], None)
    assert bound is not _record
    result = bound("plan")
    assert result["kwargs"]["available_tools"] == []


def test_build_task_loop_stage_passes_event_sink_when_supported():
    seen = {}

    def fake_task_loop(
        plan,
        *,
        conversation_id,
        objective,
        tool_runner,
        max_steps,
        max_retries_per_step,
        max_replans,
        loop_detection_enabled,
        no_progress_threshold,
        approval_mode,
        default_timeout_s,
        event_sink,
    ):
        seen["event_sink"] = event_sink
        seen["loop_detection_enabled"] = loop_detection_enabled
        seen["no_progress_threshold"] = no_progress_threshold
        seen["approval_mode"] = approval_mode
        seen["default_timeout_s"] = default_timeout_s
        snapshot = TaskLoopSnapshot(
            plan_id="plan-1",
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.COMPLETED,
            current_step_index=0,
            max_steps=max_steps,
            max_retries_per_step=max_retries_per_step,
            max_replans=max_replans,
        )
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=[],
            visible_content="ok",
            snapshot=snapshot,
        )

    plan = ThinkingPlan(intent="x", steps=[], needs_task_loop=True, risk_level=RiskLevel.SAFE, plan_id="plan-1")
    sink = lambda payload: None

    build_task_loop_stage(
        plan,
        conversation_id="conv-1",
        objective="obj",
        task_loop_fn=fake_task_loop,
        tool_runner=lambda call: None,
        replanner_fn=lambda *a, **k: None,
        max_steps=3,
        max_retries_per_step=1,
        max_replans=1,
        loop_detection_enabled=False,
        no_progress_threshold=5,
        approval_mode="approval_first",
        default_timeout_s=120.0,
        event_sink=sink,
    )

    assert seen["event_sink"] is sink
    assert seen["loop_detection_enabled"] is False
    assert seen["no_progress_threshold"] == 5
    assert seen["approval_mode"] == "approval_first"
    assert seen["default_timeout_s"] == 120.0


def test_build_task_loop_stage_injects_available_evidence_types_from_tools():
    """P5 Regression (Doc 36 Regel 6): build_task_loop_stage extrahiert
    capability_evidence_types aus ToolDescriptor-Objekten und reicht sie
    als available_evidence_types: frozenset an task_loop_fn weiter.
    """
    seen = {}

    def fake_task_loop(
        plan,
        *,
        conversation_id,
        objective,
        tool_runner,
        max_steps,
        max_retries_per_step,
        max_replans,
        available_evidence_types,
        **_kwargs,
    ):
        seen["available_evidence_types"] = available_evidence_types
        snapshot = TaskLoopSnapshot(
            plan_id="plan-1",
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.COMPLETED,
            current_step_index=0,
            max_steps=max_steps,
            max_retries_per_step=max_retries_per_step,
            max_replans=max_replans,
        )
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=[],
            visible_content="ok",
            snapshot=snapshot,
        )

    tools = [
        ToolDescriptor(name="tool_a", capability_evidence_types=["file_content", "tool_result"]),
        ToolDescriptor(name="tool_b", capability_evidence_types=["semantic_search_result"]),
        ToolDescriptor(name="tool_c"),  # keine capability_evidence_types → ignoriert
    ]
    plan = ThinkingPlan(intent="x", steps=[], needs_task_loop=True, risk_level=RiskLevel.SAFE, plan_id="plan-1")

    build_task_loop_stage(
        plan,
        conversation_id="conv-1",
        objective="obj",
        task_loop_fn=fake_task_loop,
        tool_runner=lambda call: None,
        replanner_fn=lambda *a, **k: None,
        max_steps=3,
        max_retries_per_step=1,
        max_replans=1,
        available_tools=tools,
    )

    assert isinstance(seen["available_evidence_types"], frozenset)
    assert seen["available_evidence_types"] == frozenset({
        "file_content",
        "tool_result",
        "semantic_search_result",
    })


def test_build_task_loop_stage_injects_empty_frozenset_when_no_tools():
    """Kein available_tools → leeres frozenset, kein Fehler."""
    seen = {}

    def fake_task_loop(plan, *, conversation_id, objective, tool_runner,
                       max_steps, max_retries_per_step, max_replans,
                       available_evidence_types, **_kwargs):
        seen["available_evidence_types"] = available_evidence_types
        snapshot = TaskLoopSnapshot(
            plan_id="plan-1", conversation_id=conversation_id, objective=objective,
            state=TaskLoopState.COMPLETED, current_step_index=0,
            max_steps=max_steps, max_retries_per_step=max_retries_per_step, max_replans=max_replans,
        )
        return TaskLoopResult(state=TaskLoopState.COMPLETED, stop_reason=None,
                              artifacts=[], visible_content="ok", snapshot=snapshot)

    plan = ThinkingPlan(intent="x", steps=[], needs_task_loop=True, risk_level=RiskLevel.SAFE, plan_id="plan-1")
    build_task_loop_stage(
        plan, conversation_id="conv-1", objective="obj",
        task_loop_fn=fake_task_loop, tool_runner=lambda call: None,
        replanner_fn=lambda *a, **k: None, max_steps=3,
        max_retries_per_step=1, max_replans=1, available_tools=None,
    )

    assert seen["available_evidence_types"] == frozenset()
