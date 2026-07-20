from core.task_loop.contracts import TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests._task_loop_runner_helpers import _plan, _step


def test_start_task_loop_completes_when_replan_drops_back_to_answer_only():
    replanned = ThinkingPlan(
        intent="answer_user",
        steps=[_step("answer_user", tool=None)],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-answer",
    )

    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="Need a final answer",
        tool_runner=_failing_runner,
        replanner_fn=lambda *args, **kwargs: replanned,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=2,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.stop_reason is None
    assert result.snapshot.plan_id == "plan-answer"
    assert result.snapshot.pending_step == ""
    assert result.snapshot.current_step_index == 0


def test_start_task_loop_calls_replanner_and_completes_with_new_plan():
    seen = {"calls": []}

    def runner(call):
        seen["calls"].append(call.step_id)
        if call.step_id == "step-1":
            return TaskToolResult(success=False, error="tool_failed")
        return TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]})

    def replanner(plan, *, objective, failed_step_id, failure, snapshot):
        seen["replan"] = {
            "objective": objective,
            "failed_step_id": failed_step_id,
            "error": failure.error,
            "replan_count": snapshot.replan_count,
        }
        return ThinkingPlan(
            intent=plan.intent,
            steps=[_step("step-2")],
            needs_task_loop=True,
            risk_level=plan.risk_level,
            reasoning="replanned",
            context_hints={"user_text": objective},
            plan_id="plan-2",
        )

    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="Need replanning",
        tool_runner=runner,
        replanner_fn=replanner,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=2,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.objective == "Need replanning"
    assert result.snapshot.plan_id == "plan-2"
    assert result.snapshot.replan_count == 1
    assert result.snapshot.completed_steps == ["step-2"]
    assert seen["calls"] == ["step-1", "step-2"]
    assert seen["replan"]["replan_count"] == 1


def test_replan_on_success_but_incomplete():
    seen = {"calls": [], "replan": {}}

    def runner(call):
        seen["calls"].append(call.step_id)
        return TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]})

    def replanner(plan, *, objective, failed_step_id, failure, snapshot):
        seen["replan"] = {
            "failed_step_id": failed_step_id,
            "error": failure.error,
            "replan_count": snapshot.replan_count,
        }
        return ThinkingPlan(
            intent=plan.intent,
            steps=[_step("step-2")],
            needs_task_loop=True,
            risk_level=plan.risk_level,
            context_hints={"user_text": objective},
            plan_id="plan-2",
        )

    result = start_task_loop(
        _plan(_incomplete_step()),
        conversation_id="conv-1",
        objective="Need file evidence",
        tool_runner=runner,
        replanner_fn=replanner,
        max_steps=5,
        max_retries_per_step=0,
        max_replans=2,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.plan_id == "plan-2"
    assert result.snapshot.replan_count == 1
    assert result.snapshot.completed_steps == ["step-2"]
    assert seen["calls"] == ["step-1", "step-2"]
    assert seen["replan"]["failed_step_id"] == "step-1"
    assert "objective_not_met" in seen["replan"]["error"]
    assert seen["replan"]["replan_count"] == 1


def _incomplete_step() -> PlanStep:
    return PlanStep(
        step_id="step-1",
        title="Step step-1",
        goal="Goal step-1",
        tool="demo_tool",
        tool_arguments={"step": "step-1"},
        required_evidence=["file_content"],
    )


def _failing_runner(call):
    return TaskToolResult(success=False, error="tool_failed")
