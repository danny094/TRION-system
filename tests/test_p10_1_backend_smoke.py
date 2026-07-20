"""P10.1 Backend-Smoke: prueft den echten Pfad ueber core.pipeline.runner.run_chat().

Kein WebUI, kein LLM, kein Docker; gefaket wird nur, wo sonst LLM/Docker/WebUI noetig
waere. Keine neue Test-Infrastruktur, keine neue Schicht, keine hardcodierte Tool-
Sonderliste. Test 5 deckte die in docs/implementation-plans/active/
p10-1-runtime-tool-eligibility.md dokumentierte Pre-existing Tech-Debt ab: bis
tool_resolver.py einen Fallback auf additional_evidence_needed.candidate_tools hatte,
blieb der Replan-Schritt ohne Tool. Mit dem Fallback ist Test 5 gruen.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from core.models import CoreChatRequest, Message, MessageRole
from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor
from core.output.contracts import OutputResult
from core.pipeline import runner
from core.task_loop.contracts import (
    StepExecutionResult, StepExecutionStatus, TaskLoopResult, TaskLoopSnapshot, TaskLoopState,
)
from core.task_loop.executor import TaskToolCall, TaskToolResult
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from utils.trion_home_contract import build_home_scope

_TEST_TOOL_INTENT_META = {"schema_version": 1, "source_sha256": "a" * 64, "bundle_version": "1.0.0-test"}

RAW_TOOLS_WITH_FORBIDDEN = [
    {"name": "memory_save", "description": "Save a fact.", "mcp": "memory-mcp",
     "tool_intent": {"name": "memory_save", "domain": "memory", "operation": "save", "tool_role": "primary", "tool_intent_meta": _TEST_TOOL_INTENT_META}},
    {"name": "graph_find_duplicate_nodes", "description": "Find duplicate nodes.", "mcp": "memory-mcp",
     "tool_intent": {"name": "graph_find_duplicate_nodes", "domain": "graph", "operation": "inspect", "tool_role": "forbidden_direct", "tool_intent_meta": _TEST_TOOL_INTENT_META}},
]

async def _ok_output(output_request, chat_request):
    return OutputResult(content="ok")

def _request(text: str, conversation_id: str) -> CoreChatRequest:
    return CoreChatRequest(model="test-model", messages=[Message(role=MessageRole.USER, content=text)],
                            conversation_id=conversation_id, source_adapter="pytest")

def _snapshot(plan, conversation_id, objective, **overrides):
    defaults = dict(state=TaskLoopState.REPLANNING, current_step_index=1, max_steps=10, max_retries_per_step=1, max_replans=2)
    defaults.update(overrides)
    return TaskLoopSnapshot(plan_id=plan.plan_id, conversation_id=conversation_id, objective=objective, **defaults)

def _single_step_plan(tool_name: str, plan_id: str, user_text: str = "") -> ThinkingPlan:
    return ThinkingPlan(intent="run_tools", steps=[PlanStep(step_id="s1", title="Save", goal="Save fact", tool=tool_name)],
                         needs_task_loop=True, risk_level=RiskLevel.SAFE, context_hints={"user_text": user_text}, plan_id=plan_id)

def _capture_replan_call(replanner_fn, plan, objective, step_id, failure, snapshot):
    # Patcht den Analyzer hinter build_replan, liefert die empfangenen kwargs zurueck.
    captured: dict = {}
    def _capturing_analyzer(*args, **kwargs):
        captured.update(kwargs)
        return {"intent": "answer_user", "suggested_tools": [], "steps": [], "risk_level": "safe", "reasoning": "captured"}
    with patch("core.thinking.replanner.analyze_request", _capturing_analyzer):
        replanner_fn(plan, objective=objective, failed_step_id=step_id, failure=failure, snapshot=snapshot)
    return captured

def _capturing_task_loop(captured: dict):
    # Task-Loop-Fake: faked einen Fehlschlag in s1 und ruft den echten replanner_fn auf.
    def fake_task_loop(plan, *, conversation_id, objective, tool_runner, replanner_fn, max_steps, max_retries_per_step, max_replans):
        failed = StepExecutionResult(step_id="s1", status=StepExecutionStatus.FAILED, error="boom")
        snapshot = _snapshot(plan, conversation_id, objective, max_steps=max_steps, max_retries_per_step=max_retries_per_step, max_replans=max_replans)
        captured.update(_capture_replan_call(replanner_fn, plan, objective, "s1", failed, snapshot))
        return TaskLoopResult(state=TaskLoopState.COMPLETED, stop_reason=None, artifacts=[], visible_content="ok", snapshot=snapshot)
    return fake_task_loop

def test_backend_memory_source_reaches_thinking_and_output_context():
    seen: dict = {}
    memory_items = [{"content": "Projekt TRION nutzt sechs Module."}]
    def fake_memory_source(user_text, conversation_id):
        return {"items": memory_items}
    def fake_meta_source(user_text, conversation_id):
        return {"memory": {"mode": "global_enabled"}}
    def fake_build_plan(user_text, classifier_result, **kwargs):
        seen["thinking_context"] = kwargs.get("orchestrator_context")
        return ThinkingPlan(intent="answer_user", steps=[], needs_task_loop=False, risk_level=RiskLevel.SAFE, reasoning="test plan",
                             suggested_tools=[], context_hints={"user_text": user_text}, plan_id="plan-memory-source")
    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        return OutputResult(content="ok")
    with patch.object(runner, "build_plan", fake_build_plan):
        response = asyncio.run(runner.run_chat(
            _request("Erinnerst du dich an unser TRION Projekt?", "smoke-memory"), output_fn=fake_output,
            orchestrator_context_sources={"memory": fake_memory_source, "conversation_meta": fake_meta_source},
        ))
    assert response.content == "ok"
    thinking_memory = (seen["thinking_context"] or {}).get("context", {}).get("memory")
    assert thinking_memory["items"] == memory_items
    output_memory = seen["output_context"]["orchestrator"]["context"]["memory"]
    assert output_memory["items"] == memory_items

def test_backend_forbidden_direct_is_filtered_before_planning_and_replan():
    seen: dict = {}
    captured: dict = {}
    def fake_build_plan(user_text, classifier_result, **kwargs):
        orchestrator_context = kwargs.get("orchestrator_context") or {}
        seen["planning_available_tools"] = orchestrator_context.get("available_tools")
        return _single_step_plan("memory_save", "plan-forbidden-direct", user_text)
    with patch.object(runner, "build_plan", fake_build_plan):
        response = asyncio.run(runner.run_chat(
            _request("Bitte merke dir folgende Information aus dem Gedaechtnis.", "smoke-forbidden"),
            output_fn=_ok_output, task_loop_fn=_capturing_task_loop(captured), orchestrator_raw_tools=RAW_TOOLS_WITH_FORBIDDEN,
        ))
    assert response.content == "ok"
    assert "graph_find_duplicate_nodes" not in (seen["planning_available_tools"] or [])
    replan_tools = captured.get("available_tools") or []
    replan_names = [t.get("name") if isinstance(t, dict) else t for t in replan_tools]
    assert "graph_find_duplicate_nodes" not in replan_names, (
        "Forbidden-direct Tool erreicht den Replan-Kontext ueber den rohen orchestrator_raw_tools-Passthrough "
        "in _bind_replan_context (task_loop_stage.py). Fix: bereits gefilterte Orchestrator-Tooldetails "
        "durchreichen, nicht neu filtern (keine Schatten-Autoritaet)."
    )

def test_backend_task_loop_replanner_receives_orchestrator_context():
    captured: dict = {}
    # P11.0 SP4 Korrektur (Round 2): simuliert get_available_tools() - ohne
    # gueltige tool_intent_meta waere das Tool nicht eligible.
    raw_tools = [{"name": "memory_save", "description": "Save a fact.", "mcp": "memory-mcp",
                  "tool_intent": {"name": "memory_save", "domain": "memory", "operation": "save", "tool_role": "primary", "tool_intent_meta": _TEST_TOOL_INTENT_META}}]
    def fake_build_plan(user_text, classifier_result, **kwargs):
        return _single_step_plan("memory_save", "plan-replan-context", user_text)
    with patch.object(runner, "build_plan", fake_build_plan):
        response = asyncio.run(runner.run_chat(
            _request("Bitte merke dir folgende Information aus dem Gedaechtnis.", "smoke-replan-ctx"),
            output_fn=_ok_output, task_loop_fn=_capturing_task_loop(captured), orchestrator_raw_tools=raw_tools,
        ))
    assert response.content == "ok"
    assert isinstance(captured.get("orchestrator_context"), dict) and "orchestrator" in captured["orchestrator_context"]
    tool_names = [t.get("name") if isinstance(t, dict) else t for t in (captured.get("available_tools") or [])]
    assert "memory_save" in tool_names

def test_backend_home_synonym_builds_container_inspect_args():
    seen: dict = {}
    scope = build_home_scope(
        labels={"trion.home": "true", "trion.profile": "trion-home"},
        manifest={"home_id": "home-1", "blueprint_id": "trion-home", "owner_agent": "trion", "roots": {"home": "/home/trion"}},
        available_capability_classes=["container_inspect"], verification_sources=["docker_inspect"],
    )
    def fake_orchestrator(user_text, classifier_result, raw_tools=None, context_sources=None, conversation_id="", **kwargs):
        tool = ToolDescriptor(name="container_inspect", description="Inspect a container by id or name.",
                               intent_description="Inspect container metadata and runtime details.",
                               intent_keywords=["inspect", "container"], capability_domain="container_runtime",
                               capability_operation="inspect", capability_required_args=["container_id_or_name"])
        return OrchestratorPackage(available_tools=[tool], selected_tools=[tool], classifier_result=classifier_result,
                                    context={"active_containers": {"active_home": {"container_id": "abc-123", "name": "trion-home", "home_scope": scope}}})
    def spy_build_plan(user_text, classifier_result, **kwargs):
        from core.thinking.thinking import build_plan as real_build_plan
        plan = real_build_plan(user_text, classifier_result, **kwargs)
        seen["plan"] = plan
        return plan
    with patch.object(runner, "build_plan", spy_build_plan):
        for text in ("Inspect this container.", "Was läuft gerade zuhause?"):
            response = asyncio.run(runner.run_chat(_request(text, "smoke-home"), output_fn=_ok_output, orchestrator_fn=fake_orchestrator,
                                                     orchestrator_raw_tools=[{"name": "container_inspect"}]))
            assert response.content == "ok"
            step = next((s for s in seen["plan"].steps if s.tool == "container_inspect"), None)
            assert step is not None, f"Kein container_inspect-Step fuer Text: {text!r}"
            assert step.tool_arguments.get("container_id") == "abc-123"

def test_backend_truth_reasoning_replans_to_workspace_get_after_time_result():
    seen: dict = {}
    calls: list = []
    text = "Wie viel Uhr ist es gerade? Pruefe danach /trion-home/status.txt."
    def fake_orchestrator(user_text, classifier_result, raw_tools=None, context_sources=None, conversation_id="", **kwargs):
        time_tool = ToolDescriptor(name="time_now", description="Return current UTC time and date.",
                                    intent_description="Get current time", intent_keywords=["time", "uhr"])
        file_tool = ToolDescriptor(name="workspace_get", description="Read a workspace entry by id.",
                                    intent_description="Read file or document content from the workspace.",
                                    intent_keywords=["file", "read", "workspace", "document"])
        return OrchestratorPackage(available_tools=[time_tool, file_tool], selected_tools=[time_tool], context={}, classifier_result=classifier_result)
    def fake_task_loop(plan, *, conversation_id, objective, tool_runner, replanner_fn, max_steps, max_retries_per_step, max_replans):
        seen["initial_suggested_tools"] = list(plan.suggested_tools)
        step1 = plan.steps[0]
        calls.append(step1.tool)
        tool_runner(TaskToolCall(tool_name=step1.tool, step_id=step1.step_id))
        ok = StepExecutionResult(step_id=step1.step_id, status=StepExecutionStatus.SUCCESS, output={"utc_iso": "2026-06-16T10:00:00Z"})
        snapshot = _snapshot(plan, conversation_id, objective, max_steps=max_steps, max_retries_per_step=max_retries_per_step,
                              max_replans=max_replans, completed_steps=[step1.step_id])
        replanned = replanner_fn(plan, objective=objective, failed_step_id=step1.step_id, failure=ok, snapshot=snapshot)
        seen["replanned_steps"] = [s.tool for s in replanned.steps]
        if replanned.needs_task_loop and replanned.steps and replanned.steps[0].tool:
            step2 = replanned.steps[0]
            calls.append(step2.tool)
            tool_runner(TaskToolCall(tool_name=step2.tool, step_id=step2.step_id))
        return TaskLoopResult(state=TaskLoopState.COMPLETED, stop_reason=None, artifacts=[], visible_content="ok", snapshot=snapshot)
    def tool_runner(call):
        return TaskToolResult(success=True, error=None)
    response = asyncio.run(runner.run_chat(_request(text, "smoke-truth"), output_fn=_ok_output, task_loop_fn=fake_task_loop,
                                            orchestrator_fn=fake_orchestrator, tool_runner=tool_runner,
                                            orchestrator_raw_tools=[{"name": "time_now"}, {"name": "workspace_get"}]))
    assert response.content == "ok"
    assert seen["initial_suggested_tools"] == ["time_now"]
    assert calls == ["time_now", "workspace_get"], (
        "tool_resolver.py::resolved_suggested_tools() soll additional_evidence_needed."
        "candidate_tools als Fallback nutzen, damit der Replan-Schritt workspace_get "
        f"waehlt (replanned_steps={seen.get('replanned_steps')!r}, calls={calls!r})."
    )
