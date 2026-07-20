from dataclasses import replace

import pytest

from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.plan_contract_validator import issue_followup_step_receipt, issue_initial_step_receipt
from core.pipeline.receipt_validation import build_step_receipt_validator
from core.task_loop.contracts import StepExecutionStatus, StepOperationExecution, TaskLoopSnapshot, TaskLoopState
from core.task_loop.executor import TaskToolResult
from core.task_loop.runner import run_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.operation_contract_context import canonical_contract_context


def _context():
    return canonical_contract_context(allowed_operations=("list",), allowed_transitions=("list->logs",))


def _tools():
    return [
        ToolDescriptor("inventory", capability_domain="container_runtime", capability_operation="list",
                       capability_evidence_types=[], capability_target_scopes=["runtime_state"], capability_risk="read_only"),
        ToolDescriptor("logs", capability_domain="container_runtime", capability_operation="logs",
                       capability_evidence_types=[], capability_target_scopes=["runtime_state"], capability_risk="read_only"),
    ]


def _plan(first="s0", second="s1"):
    return ThinkingPlan(
        "run", [PlanStep(first, "List", "List", tool="inventory"), PlanStep(second, "Logs", "Logs", tool="logs")],
        True, RiskLevel.SAFE, plan_id="plan",
    )


def _three_step_plan():
    return ThinkingPlan(
        "run",
        [
            PlanStep("s0", "List", "List", tool="inventory"),
            PlanStep("s1", "Logs", "Logs", tool="logs"),
            PlanStep("s2", "Logs again", "Logs", tool="logs"),
        ],
        True, RiskLevel.SAFE, plan_id="plan",
    )


def _receipts():
    initial = issue_initial_step_receipt("s0", context=_context())
    predecessor = StepOperationExecution(initial, StepExecutionStatus.SUCCESS)
    followup = issue_followup_step_receipt("s1", predecessor, context=_context())
    assert initial and followup
    return initial, followup


def _run(plan, snapshot, receipt):
    calls, events = [], []
    result = run_task_loop(
        plan, snapshot,
        lambda call: calls.append(call.step_id) or TaskToolResult(True, {}),
        step_receipts={receipt.step_id: receipt}, receipt_mode=True,
        receipt_validator=build_step_receipt_validator(_context(), _tools(), plan),
        event_sink=lambda event: events.append(dict(event)),
    )
    return result, calls, events


def test_exact_completed_prefix_allows_followup():
    initial, followup = _receipts()
    snapshot = TaskLoopSnapshot(
        "plan", "conv", "run", TaskLoopState.EXECUTING, 1, 4, 0,
        completed_steps=["s0"],
        step_operation_executions=[StepOperationExecution(initial, StepExecutionStatus.SUCCESS)],
    )
    result, calls, _events = _run(_plan(), snapshot, followup)
    assert result.state is TaskLoopState.COMPLETED
    assert calls == ["s1"]


@pytest.mark.parametrize("completed,executions", [
    (["s1"], lambda receipt: [StepOperationExecution(replace(receipt, step_id="s1"), StepExecutionStatus.SUCCESS)]),
    (["s0"], lambda _receipt: []),
    (["s0"], lambda receipt: [StepOperationExecution(receipt, StepExecutionStatus.SUCCESS)] * 2),
    (["s0", "s1"], lambda receipt: [StepOperationExecution(receipt, StepExecutionStatus.SUCCESS)]),
    (["s0"], lambda receipt: [StepOperationExecution(replace(receipt, step_id="s1"), StepExecutionStatus.SUCCESS)]),
    (["s0"], lambda receipt: [StepOperationExecution(receipt, StepExecutionStatus.FAILED)]),
    (["s0"], lambda receipt: [StepOperationExecution(receipt, StepExecutionStatus.TIMEOUT)]),
    (["s0"], lambda receipt: [StepOperationExecution(receipt, StepExecutionStatus.SKIPPED)]),
])
def test_invalid_prefix_blocks_before_tool_start(completed, executions):
    initial, followup = _receipts()
    snapshot = TaskLoopSnapshot(
        "plan", "conv", "run", TaskLoopState.EXECUTING, 1, 4, 0,
        completed_steps=completed, step_operation_executions=executions(initial),
    )
    result, calls, events = _run(_plan(), snapshot, followup)
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []
    assert all(event.get("type") != "tool_start" for event in events)


@pytest.mark.parametrize("plan", [_plan("s0", "s0"), _plan("", "s1")])
def test_duplicate_or_empty_plan_step_id_blocks_initial_tool_start(plan):
    initial = issue_initial_step_receipt(plan.steps[0].step_id, context=_context())
    if initial is None:
        initial = replace(_receipts()[0], step_id=plan.steps[0].step_id)
    snapshot = TaskLoopSnapshot("plan", "conv", "run", TaskLoopState.EXECUTING, 0, 4, 0)
    result, calls, events = _run(plan, snapshot, initial)
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []
    assert all(event.get("type") != "tool_start" for event in events)


def test_index_zero_rejects_foreign_execution_history():
    initial, _followup = _receipts()
    snapshot = TaskLoopSnapshot(
        "plan", "conv", "run", TaskLoopState.EXECUTING, 0, 4, 0,
        step_operation_executions=[StepOperationExecution(initial, StepExecutionStatus.SUCCESS)],
    )
    result, calls, _events = _run(_plan(), snapshot, initial)
    assert result.state is TaskLoopState.BLOCKED
    assert calls == []


@pytest.mark.parametrize("completed,execution_ids", [
    (["s0", "s1"], ["s1", "s0"]),
    (["s0", "s1"], ["s0"]),
    (["s0", "s1"], ["s0", "s0"]),
    (["s0", "s1"], ["s0", "s1", "s2"]),
    (["s0", "s2"], ["s0", "s2"]),
])
def test_three_step_prefix_rejects_reorder_gap_duplicate_extra_and_completed_mismatch(
    completed, execution_ids,
):
    initial, followup = _receipts()
    receipts = {
        "s0": initial,
        "s1": followup,
        "s2": replace(followup, step_id="s2"),
    }
    executions = [
        StepOperationExecution(receipts[step_id], StepExecutionStatus.SUCCESS)
        for step_id in execution_ids
    ]
    current = replace(followup, step_id="s2")
    snapshot = TaskLoopSnapshot(
        "plan", "conv", "run", TaskLoopState.EXECUTING, 2, 4, 0,
        completed_steps=completed, step_operation_executions=executions,
    )

    result, calls, events = _run(_three_step_plan(), snapshot, current)

    assert result.state is TaskLoopState.BLOCKED
    assert calls == []
    assert all(event.get("type") != "tool_start" for event in events)
