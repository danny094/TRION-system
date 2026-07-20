from dataclasses import replace

from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import PlanStep


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        plan_id="plan-1",
        conversation_id="conv-1",
        objective="Starte einen Python Container und pruefe die Ausgabe.",
        state=TaskLoopState.EXECUTING,
        current_step_index=0,
        max_steps=10,
        max_retries_per_step=2,
        max_replans=3,
    )


def test_task_loop_snapshot_requires_and_preserves_objective():
    snapshot = _snapshot()
    reflected = snapshot.transition_to(TaskLoopState.REFLECTING)

    assert reflected.objective == snapshot.objective
    assert reflected.max_steps == 10
    assert reflected.max_retries_per_step == 2
    assert reflected.max_replans == 3


def test_task_loop_contract_exposes_replanning_state():
    snapshot = replace(_snapshot(), state=TaskLoopState.REFLECTING)
    replanning = snapshot.transition_to(TaskLoopState.REPLANNING)
    executing = replanning.transition_to(TaskLoopState.EXECUTING)

    assert replanning.state == TaskLoopState.REPLANNING
    assert executing.objective == snapshot.objective


def test_plan_step_supports_step_specific_timeout():
    step = PlanStep(
        step_id="deploy",
        title="Container deployen",
        goal="Container starten",
        tool="deploy_container",
        timeout_s=180.0,
    )

    assert step.timeout_s == 180.0
