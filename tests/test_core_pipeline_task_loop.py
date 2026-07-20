import asyncio

from core.output.contracts import OutputResult
from core.task_loop.contracts import TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolCall
from core.pipeline import runner
from core.pipeline.thinking_stage import ThinkingStageResult
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from tests._core_pipeline_request_helpers import core_pipeline_request
from tests.operation_contract_context import canonical_contract_context


def _tool_detail() -> dict:
    return {
        "name": "deploy_container",
        "capability_domain": "container_runtime",
        "capability_operation": "deploy",
        "capability_evidence_types": ["runtime_state"],
        "capability_required_args": [],
        "capability_target_scopes": ["runtime_state"],
        "capability_risk": "mutating",
        "capability_output_schema": "mcp_output_schema",
    }


def _thinking_context(fingerprint: str) -> dict:
    del fingerprint
    frame = canonical_contract_context(
        primary_operation="execute", allowed_operations=("execute",), allowed_transitions=(),
        mutating_action=True,
    )["routing_frame"]
    return {
        "selected_tool_details": [_tool_detail()],
        "context": {"routing_frame": frame},
    }


def test_core_task_loop_path_passes_full_context_to_output(monkeypatch):
    seen = {}

    def build_task_plan(user_text, classifier_result):
        return ThinkingPlan(
            intent="run_tools",
            steps=[
                PlanStep(
                    step_id="deploy",
                    title="Deploy",
                    goal="Run deployment",
                    tool="deploy_container",
                    tool_arguments={"blueprint": "python"},
                )
            ],
            needs_task_loop=True,
            risk_level=RiskLevel.SAFE,
            context_hints={"user_text": user_text},
            plan_id="task-plan-1",
        )

    def run_task_loop(plan, *, conversation_id, objective, tool_runner, max_steps, max_retries_per_step, max_replans):
        seen["plan_id"] = plan.plan_id
        seen["conversation_id"] = conversation_id
        seen["objective"] = objective
        seen["budgets"] = {
            "max_steps": max_steps,
            "max_retries_per_step": max_retries_per_step,
            "max_replans": max_replans,
        }
        tool_result = tool_runner(TaskToolCall(tool_name="deploy_container", step_id="deploy"))
        seen["tool_error"] = tool_result.error
        snapshot = TaskLoopSnapshot(
            plan_id=plan.plan_id,
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.COMPLETED,
            current_step_index=1,
            max_steps=10,
            max_retries_per_step=1,
            completed_steps=["deploy"],
            artifacts=[{"id": "artifact-1"}],
        )
        return TaskLoopResult(
            state=TaskLoopState.COMPLETED,
            stop_reason=None,
            artifacts=[{"id": "artifact-1"}],
            visible_content="Task loop completed.",
            snapshot=snapshot,
        )

    async def fake_output(output_request, chat_request):
        seen["output_context"] = output_request.context
        return OutputResult(content="loop answer")

    monkeypatch.setattr(
        runner,
        "build_thinking_stage",
        lambda user_text, classifier_result, **_kw: ThinkingStageResult(
            plan=build_task_plan(user_text, classifier_result),
            thinking_context=_thinking_context("fp-task-plan-1"),
        ),
    )
    monkeypatch.setattr(runner, "get_task_loop_max_steps", lambda: 12)
    monkeypatch.setattr(runner, "get_task_loop_max_retries_per_step", lambda: 3)
    monkeypatch.setattr(runner, "get_task_loop_max_replans", lambda: 4)
    monkeypatch.setattr(runner, "verify_plan", lambda *a, **kw: VerifierResult(verdict=Verdict.APPROVED, reason="test_bypass"))

    response = asyncio.run(
        runner.run_chat(
            core_pipeline_request("Deploy the python container"),
            output_fn=fake_output,
            task_loop_fn=run_task_loop,
        )
    )

    task_loop_context = seen["output_context"]["task_loop"]

    assert response.content == "loop answer"
    assert response.validation_passed is True
    assert seen["plan_id"] == "task-plan-1"
    assert seen["conversation_id"] == "p0-test"
    assert seen["objective"] == "Deploy the python container"
    assert seen["budgets"] == {"max_steps": 12, "max_retries_per_step": 3, "max_replans": 4}
    assert seen["tool_error"] == "tool_runner_missing:deploy_container"
    assert task_loop_context["state"] == "completed"
    assert task_loop_context["visible_content"] == "Task loop completed."
    assert task_loop_context["completion_status"] == "complete"
    assert task_loop_context["artifacts"] == [{"id": "artifact-1"}]
    assert "objective" not in task_loop_context["snapshot"]
    assert "completed_steps" not in task_loop_context["snapshot"]
    assert task_loop_context["snapshot"]["artifacts"] == [{"artifact_type": "artifact"}]


def test_core_task_loop_path_passes_replanner_into_task_loop(monkeypatch):
    seen = {}

    def build_task_plan(user_text, classifier_result):
        return ThinkingPlan(
            intent="run_tools",
            steps=[PlanStep(step_id="deploy", title="Deploy", goal="Run deployment", tool="deploy_container")],
            needs_task_loop=True,
            risk_level=RiskLevel.SAFE,
            context_hints={"user_text": user_text},
            plan_id="task-plan-2",
        )

    def run_task_loop(plan, *, conversation_id, objective, tool_runner, replanner_fn, max_steps, max_retries_per_step, max_replans):
        seen["replanner_name"] = getattr(replanner_fn, "__name__", "")
        snapshot = TaskLoopSnapshot(
            plan_id=plan.plan_id,
            conversation_id=conversation_id,
            objective=objective,
            state=TaskLoopState.COMPLETED,
            current_step_index=1,
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

    async def fake_output(output_request, chat_request):
        return OutputResult(content="loop answer")

    monkeypatch.setattr(
        runner,
        "build_thinking_stage",
        lambda user_text, classifier_result, **_kw: ThinkingStageResult(
            plan=build_task_plan(user_text, classifier_result),
            thinking_context=_thinking_context("fp-task-plan-2"),
        ),
    )
    monkeypatch.setattr(runner, "verify_plan", lambda *a, **kw: VerifierResult(verdict=Verdict.APPROVED, reason="test_bypass"))

    response = asyncio.run(
        runner.run_chat(
            core_pipeline_request("Deploy it"),
            output_fn=fake_output,
            task_loop_fn=run_task_loop,
        )
    )

    assert response.content == "loop answer"
    assert seen["replanner_name"] == "build_replan"
