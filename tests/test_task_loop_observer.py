import asyncio

from core.classifier.contracts import Category
from core.models import CoreChatRequest, Message, MessageRole
from core.orchestrator.contracts import OrchestratorPackage, ToolDescriptor
from core.output.contracts import OutputResult
from core.pipeline import runner
from core.pipeline.orchestrator_stage import (
    TOOL_TRUTH_FALLBACK,
    TOOL_TRUTH_ORCHESTRATOR_FILTERED,
)
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult

from tests._orchestrator_classifier_helpers import make_classifier_result


def _request(text: str = "Bitte ausfuehren") -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content=text)],
        conversation_id="observer-test",
        source_adapter="pytest",
    )


def test_run_chat_calls_task_loop_observer_with_task_context(monkeypatch):
    seen = {}

    def build_task_plan(user_text, classifier_result):
        return ThinkingPlan(
            intent="run_tools",
            steps=[PlanStep(step_id="step-1", title="Step", goal="Goal", tool=None)],
            needs_task_loop=True,
            risk_level=RiskLevel.SAFE,
            context_hints={"user_text": user_text},
            plan_id="plan-observer",
        )

    def fake_task_loop(plan, *, conversation_id, objective, tool_runner, max_steps, max_retries_per_step, max_replans):
        active_plan = ThinkingPlan(
            intent=plan.intent, steps=list(plan.steps), needs_task_loop=True,
            risk_level=plan.risk_level, plan_id="plan-replanned",
        )
        snapshot = TaskLoopSnapshot(
            plan_id=active_plan.plan_id,
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.WAITING,
            current_step_index=0,
            max_steps=max_steps,
            max_retries_per_step=max_retries_per_step,
            max_replans=max_replans,
            pending_step="step-1",
        )
        return TaskLoopResult(
            state=TaskLoopState.WAITING,
            stop_reason=None,
            artifacts=[],
            visible_content="waiting",
            snapshot=snapshot,
            active_plan=active_plan,
        )

    def observe_task_loop(**kwargs):
        seen.update(kwargs)

    async def fake_output(output_request, chat_request):
        return OutputResult(content="ok")

    monkeypatch.setattr(runner, "build_plan", build_task_plan)
    monkeypatch.setattr(runner, "verify_plan", lambda *a, **kw: VerifierResult(verdict=Verdict.APPROVED, reason="ok"))

    response = asyncio.run(
        runner.run_chat(
            _request(),
            output_fn=fake_output,
            task_loop_fn=fake_task_loop,
            task_loop_observer=observe_task_loop,
            orchestrator_raw_tools=[{"name": "workspace_get"}],
        )
    )

    assert response.content == "ok"
    assert seen["plan"].plan_id == "plan-replanned"
    assert seen["task_loop_result"].state == TaskLoopState.WAITING
    assert seen["task_loop_result"].snapshot.pending_step == "step-1"
    assert seen["orchestrator_context"] == {}
    assert seen["available_tools"] == [{"name": "workspace_get"}]
    assert seen["tool_truth_source"] == TOOL_TRUTH_FALLBACK, (
        "Kein Orchestrator-Block vorhanden -> available_tools ist hier die rohe "
        "orchestrator_raw_tools-Liste. P11 SP3-F Fund C: das muss am Namen "
        "available_tools nicht erkennbar sein, aber tool_truth_source muss es "
        "explizit als Fallback markieren, nicht als orchestrator_filtered."
    )


def test_run_chat_calls_task_loop_observer_with_orchestrator_filtered_tool_truth_source(monkeypatch):
    """Gegenstueck: laeuft der Orchestrator und liefert eine (auch leere)
    available_tool_details-Liste, muss tool_truth_source orchestrator_filtered
    sein, nicht fallback_tools (P11 SP3-F Fund C)."""
    seen = {}

    def build_task_plan(user_text, classifier_result):
        return ThinkingPlan(
            intent="run_tools",
            steps=[PlanStep(step_id="step-1", title="Step", goal="Goal", tool=None)],
            needs_task_loop=True,
            risk_level=RiskLevel.SAFE,
            context_hints={"user_text": user_text},
            plan_id="plan-observer-filtered",
        )

    def fake_task_loop(plan, *, conversation_id, objective, tool_runner, max_steps, max_retries_per_step, max_replans):
        snapshot = TaskLoopSnapshot(
            plan_id=plan.plan_id,
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.WAITING,
            current_step_index=0,
            max_steps=max_steps,
            max_retries_per_step=max_retries_per_step,
            max_replans=max_replans,
            pending_step="step-1",
        )
        return TaskLoopResult(
            state=TaskLoopState.WAITING,
            stop_reason=None,
            artifacts=[],
            visible_content="waiting",
            snapshot=snapshot,
        )

    def fake_orchestrator(user_text, classifier_result, raw_tools=None, context_sources=None, conversation_id="", **kwargs):
        tool = ToolDescriptor(name="workspace_get", source="workspace-mcp")
        return OrchestratorPackage(
            available_tools=[tool],
            selected_tools=[tool],
            context={},
            classifier_result=make_classifier_result(needs_orchestrator=True, category=Category.INFORMATION),
        )

    def observe_task_loop(**kwargs):
        seen.update(kwargs)

    async def fake_output(output_request, chat_request):
        return OutputResult(content="ok")

    # Echtes classify("Bitte ausfuehren") liefert category=information/
    # direct_to_thinking (siehe Schwester-Test oben -> tool_truth_source==
    # FALLBACK, weil der Orchestrator-Gate dafuer nie anspringt). Damit dieser
    # Test wirklich den orchestrator_filtered-Zweig prueft (statt zufaellig
    # vom Klassifizierer-Wortlaut abzuhaengen), wird classify() hart auf
    # category=TOOL/needs_orchestrator=True gestellt - das ist exakt die
    # Bedingung, unter der core/routing_frame/gates.py den Orchestrator ueberhaupt
    # erst durchlaesst (intent_kind=="action_request").
    monkeypatch.setattr(runner, "classify", lambda user_text: make_classifier_result(needs_orchestrator=True, category=Category.TOOL))
    monkeypatch.setattr(runner, "build_plan", build_task_plan)
    monkeypatch.setattr(runner, "verify_plan", lambda *a, **kw: VerifierResult(verdict=Verdict.APPROVED, reason="ok"))

    response = asyncio.run(
        runner.run_chat(
            _request(),
            output_fn=fake_output,
            task_loop_fn=fake_task_loop,
            task_loop_observer=observe_task_loop,
            orchestrator_fn=fake_orchestrator,
            orchestrator_raw_tools=[{"name": "workspace_get"}],
        )
    )

    assert response.content == "ok"
    assert seen["tool_truth_source"] == TOOL_TRUTH_ORCHESTRATOR_FILTERED, (
        "Orchestrator ist gelaufen und hat eine gefilterte Liste geliefert -> "
        "tool_truth_source darf nicht fallback_tools sein."
    )
