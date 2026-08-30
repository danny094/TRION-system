from core.task_loop.contracts import StopReason, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.runner import run_task_loop
from core.task_loop.task_loop import continue_task_loop, start_task_loop
from tests._task_loop_runner_helpers import _plan, _risky_step, _step


_TOOL_DETAILS = {"demo_tool": {"name": "demo_tool", "capability_required_args": []}}


def test_start_task_loop_completes_multi_step_plan():
    seen = []

    def runner(call):
        seen.append((call.step_id, call.arguments))
        return TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]})

    result = start_task_loop(
        _plan(_step("step-1"), _step("step-2")),
        conversation_id="conv-1",
        objective="Launch the workflow",
        tool_runner=runner,
        tool_details_by_name=_TOOL_DETAILS,
        max_steps=5,
        max_replans=2,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.stop_reason is None
    assert result.snapshot.objective == "Launch the workflow"
    assert result.snapshot.completed_steps == ["step-1", "step-2"]
    assert result.snapshot.current_step_index == 2
    assert result.artifacts[0] == {"id": "step-1"}
    assert result.artifacts[2] == {"id": "step-2"}
    assert result.artifacts[1]["artifact_type"] == "tool_result"
    assert result.artifacts[3]["artifact_type"] == "tool_result"
    assert seen == [("step-1", {"step": "step-1"}), ("step-2", {"step": "step-2"})]


def test_run_task_loop_enters_waiting_on_skipped_step():
    snapshot = TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="Need user decision",
        state=TaskLoopState.EXECUTING,
        current_step_index=0,
        max_steps=5,
        max_retries_per_step=1,
        max_replans=2,
    )

    result = run_task_loop(
        _plan(_step("step-1", tool=None)),
        snapshot,
        lambda call: (_ for _ in ()).throw(AssertionError("runner must not be called")),
    )

    assert result.state == TaskLoopState.WAITING
    assert result.stop_reason == StopReason.USER_DECISION_NEEDED
    assert result.snapshot.pending_step == "step-1"
    assert result.snapshot.objective == "Need user decision"


def test_continue_task_loop_can_cancel_waiting_snapshot():
    waiting = _waiting_snapshot(pending_step="step-1")

    result = continue_task_loop(waiting, "cancel", _plan(_step("step-1")), tool_runner=lambda call: None)

    assert result.state == TaskLoopState.CANCELLED
    assert result.stop_reason == StopReason.USER_CANCELLED
    assert result.snapshot.objective == "Keep original objective"


def test_continue_task_loop_advances_after_waiting():
    waiting = _waiting_snapshot(pending_step="step-1", artifacts=[{"id": "artifact-before"}])
    plan = _plan(_step("step-1", tool=None), _step("step-2"))

    def runner(call):
        return TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]})

    result = continue_task_loop(
        waiting, "weiter", plan, tool_runner=runner, tool_details_by_name=_TOOL_DETAILS,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.objective == "Keep original objective"
    assert result.snapshot.completed_steps == ["step-2"]
    assert result.artifacts[0] == {"id": "artifact-before"}
    assert result.artifacts[1] == {"id": "step-2"}
    assert result.artifacts[2]["artifact_type"] == "tool_result"


def test_start_task_loop_manual_mode_waits_before_tool_execution():
    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="Need approval first",
        tool_runner=lambda call: (_ for _ in ()).throw(AssertionError("runner must not be called")),
        approval_mode="approval_first",
        max_steps=5,
        max_replans=2,
    )

    assert result.state == TaskLoopState.WAITING
    assert result.stop_reason == StopReason.RISK_GATE_REQUIRED
    assert result.snapshot.pending_step == "step-1"


def test_start_task_loop_risk_based_mode_waits_for_risky_step():
    result = start_task_loop(
        _plan(_risky_step("step-1")),
        conversation_id="conv-1",
        objective="Risky step needs approval",
        tool_runner=lambda call: (_ for _ in ()).throw(AssertionError("runner must not be called")),
        approval_mode="risk_based",
        max_steps=5,
        max_replans=2,
    )

    assert result.state == TaskLoopState.WAITING
    assert result.stop_reason == StopReason.RISK_GATE_REQUIRED


def test_continue_task_loop_retries_same_step_after_risk_gate_waiting():
    waiting = _waiting_snapshot(
        pending_step="step-1",
        approval_mode="permissive",
        stop_reason=StopReason.RISK_GATE_REQUIRED,
    )
    seen = []

    def runner(call):
        seen.append(call.step_id)
        return TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]})

    result = continue_task_loop(
        waiting, "freigeben", _plan(_step("step-1")), tool_runner=runner,
        tool_details_by_name=_TOOL_DETAILS,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert result.snapshot.completed_steps == ["step-1"]
    assert seen == ["step-1"]


def test_start_task_loop_permissive_mode_runs_risky_step_without_approval_tool_flag():
    seen = []

    def runner(call):
        seen.append(call.step_id)
        return TaskToolResult(success=True, result={"artifacts": [{"id": call.step_id}]})

    result = start_task_loop(
        _plan(_risky_step("step-1")),
        conversation_id="conv-1",
        objective="Risky but permitted",
        tool_runner=runner,
        tool_details_by_name=_TOOL_DETAILS,
        approval_mode="permissive",
        max_steps=5,
        max_replans=2,
    )

    assert result.state == TaskLoopState.COMPLETED
    assert seen == ["step-1"]


def test_start_task_loop_permissive_mode_waits_for_approval_required_tool():
    result = start_task_loop(
        _plan(_step("step-1")),
        conversation_id="conv-1",
        objective="Approval-required tool",
        tool_runner=lambda call: (_ for _ in ()).throw(AssertionError("runner must not be called")),
        approval_mode="permissive",
        approval_required_tools=["demo_tool"],
        max_steps=5,
        max_replans=2,
    )

    assert result.state == TaskLoopState.WAITING
    assert result.stop_reason == StopReason.RISK_GATE_REQUIRED


def _waiting_snapshot(**updates) -> TaskLoopSnapshot:
    data = {
        "plan_id": "plan-1",
        "conversation_id": "conv-1",
        "objective": "Keep original objective",
        "state": TaskLoopState.WAITING,
        "current_step_index": 0,
        "max_steps": 5,
        "max_retries_per_step": 1,
        "max_replans": 2,
    }
    data.update(updates)
    return TaskLoopSnapshot(**data)
